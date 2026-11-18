"""算子处理器抽象与公共数据结构。

约定（见 docs/预训练文本算子开发规范-V1.0.md）：
- 算子是纯函数：记录进 → 结果出；不落盘、不保留任何跨请求状态
- HTTP 壳（common.server）负责传输、外壳、参数解析、超限拦截；处理器只写核心逻辑
- 单条记录处理失败不得中断整批：用 safe_map 或自行 try/except，
  失败记录返回 tags=["处理失败"]、action="review"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional


@dataclass
class OperatorContext:
    """一次调用的原始输入信息（HTTP 壳构造）。

    文件级算子（#2 异常过滤、#5/#6/#7 容器提取、#10 编码归一化）需要原始
    字节做魔数校验/编码检测/容器解析——records 已是壳解析后的文本，二进制
    信息会丢失，因此通过 context 透传。
    """

    raw: bytes = b""      # 上传文件原始字节
    filename: str = ""    # 上传文件名（含后缀）

# ---- action 枚举（规范 4.2）----
ACTION_KEEP = "keep"      # 保留
ACTION_REMOVE = "remove"  # 建议删除/隔离
ACTION_REVIEW = "review"  # 建议人工复核

# ---- 业务标签（规范 4.3：使用主表"拦截处理"列标签原文）----
TAG_PROCESSED_FAIL = "处理失败"
TAG_UNPARSEABLE = "原始文件-无法解析"
TAG_ENCODING_ERROR = "原始文件-编码异常"
TAG_EMPTY_FILE = "原始文件-空"
TAG_CORRUPT = "原始文件-损坏"


@dataclass
class TextRecord:
    """输入记录。jsonl 每行一条；非结构化文件整体作为一条。"""

    record_id: str
    text: str
    metadata: dict = field(default_factory=dict)
    # metadata 约定键：
    #   parseError   该记录解析失败的异常信息（解码失败/JSON 行非法等）
    #   decodeFailed True 表示字节无法解码为文本（#2/#10 等算子按业务处理）


@dataclass
class RecordResult:
    """输出记录，序列化为外壳 data[] 的一个元素。"""

    fieldName: str
    tags: List[str] = field(default_factory=list)
    action: str = ACTION_KEEP
    # 算子业务字段（text / hashValue / length / errorRate / rate / texts / hits ...），
    # 命名按规范 4.4 映射总表
    fields: dict = field(default_factory=dict)
    errorCode: Optional[str] = None   # 单条失败时填规范 4.5 枚举
    error: Optional[str] = None       # 人可读失败原因

    def to_dict(self) -> dict:
        # status 为主表 U 列兼容字段：1=放行/处理成功，0=过滤/需复核（由 action 派生）
        status = 1 if self.action == ACTION_KEEP else 0
        data = {"fieldName": self.fieldName, "tags": self.tags, "action": self.action,
                "status": status}
        if self.errorCode is not None:
            data["errorCode"] = self.errorCode
        if self.error is not None:
            data["error"] = self.error
        data.update(self.fields)
        return data


@dataclass
class OperatorOutput:
    """process 返回值。extras 为响应体顶层附加字段（如去重的 newFingerprints）。"""

    results: List[RecordResult] = field(default_factory=list)
    extras: dict = field(default_factory=dict)


class Operator:
    """算子基类。子类在 model/network.py 继承并实现 process。"""

    detection: str = ""          # 算子标识，= 主表英文名 PTt_xxx（规范 2.2）
    name: str = ""               # 主表工具名称
    tool_type: str = "规则型"     # 规则型 / 小模型 / 算法（以主表为准）
    version: str = "1.0.0"
    default_params: dict = {}    # 默认参数，与 configs/config.yaml 保持一致（规范 5.1）

    def process(
        self,
        records: List[TextRecord],
        params: Optional[dict] = None,
        resources: Optional[dict] = None,
        context: Optional["OperatorContext"] = None,
    ) -> OperatorOutput:
        """核心逻辑。records 为一次调用的全部输入记录。

        params: form 字段 param_xxx 去前缀后的键值（中文键，值为字符串），
                已与 default_params 合并（请求优先）
        resources: 可选资源文件字节数据，键为 fingerprint_library / lexicon /
                dictionary / topic_table（规范第 7、8 章）
        context: 原始输入信息（raw 字节 + filename），文件级算子使用
        """
        raise NotImplementedError


def safe_map(
    records: List[TextRecord],
    fn: Callable[[TextRecord], RecordResult],
    error_code: str = "INTERNAL_ERROR",
) -> List[RecordResult]:
    """逐条执行 fn，单条异常不中断整批（规范 4.5）。"""
    results = []
    for record in records:
        try:
            results.append(fn(record))
        except Exception as exc:  # noqa: BLE001 - 单条失败必须隔离
            results.append(
                RecordResult(
                    fieldName=record.record_id,
                    tags=[TAG_PROCESSED_FAIL],
                    action=ACTION_REVIEW,
                    errorCode=error_code,
                    error=str(exc),
                )
            )
    return results


# ---- param 值解析助手（规范 5.2：值为中文原值字符串）----

_TRUE_CN = {"启用", "开", "保留", "是", "true", "True", "TRUE", "1"}
_FALSE_CN = {"禁用", "关闭", "关", "删除", "丢弃", "否", "false", "False", "FALSE", "0"}


def parse_bool(value: Any, default: bool = True) -> bool:
    """解析布尔参数。启用/开/保留/是 → True；禁用/关/删除/否 → False。"""
    if value is None:
        return default
    text = str(value).strip()
    if text in _TRUE_CN:
        return True
    if text in _FALSE_CN:
        return False
    raise ValueError(f"非法布尔参数值: {value!r}（应为 启用/禁用 等中文原值）")


def parse_int(value: Any, default: Optional[int] = None) -> int:
    if value is None or str(value).strip() == "":
        return default
    return int(str(value).strip())


def parse_float(value: Any, default: Optional[float] = None) -> float:
    if value is None or str(value).strip() == "":
        return default
    return float(str(value).strip())


def parse_ratio(value: Any, default: Optional[float] = None) -> float:
    """解析比例/百分比参数：`80%` / `80` / `0.8` 均返回 0.8。

    主表配置项习惯写百分数（80%、30%），旧接口也接受小数；>1 视为百分数。
    格式非法时抛 ValueError，由算子转 PARAM_INVALID。
    """
    if value is None or str(value).strip() == "":
        return default
    text = str(value).strip()
    is_percent = text.endswith("%") or text.endswith("％")
    text = text.rstrip("%％").strip()
    number = float(text)
    if is_percent or number > 1:
        return number / 100.0
    return number


def parse_list(value: Any, sep: str = "；") -> List[str]:
    """解析多选列表（规范 5.2：中文分号分隔）。空值返回空列表。"""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value).split(sep) if item.strip()]
