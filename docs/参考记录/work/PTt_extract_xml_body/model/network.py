"""PTt_extract_xml_body：XML抽出正文（规则型，#4 清洗·正文）。

逻辑迁移自 demo（A 级复用）。ElementTree 解析，去标签/属性只留正文文字。
参数（Excel 配置项）：
- param_正文提取范围：输入节点名称，默认全文
- param_标签过滤：启用=仅保留文本（默认）；禁用=保留去 XML 声明后的原文
- param_属性过滤：启用=属性不进入正文（默认；对文本输出天然成立，仅记录口径）
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import List, Optional

from common.operator_base import (
    ACTION_KEEP,
    ACTION_REMOVE,
    Operator,
    OperatorContext,
    OperatorOutput,
    RecordResult,
    TAG_UNPARSEABLE,
    TextRecord,
    parse_bool,
    safe_map,
)

_XML_DECL_RE = re.compile(r"<\?xml[^>]*\?>", re.IGNORECASE)


def _strip_decl(xml_text: str) -> str:
    return _XML_DECL_RE.sub("", xml_text).strip()


def extract_xml_text(xml_text: str, scope: Optional[str], tag_filter: bool) -> str:
    """按范围抽取 XML 文本。scope=None 提取全文，否则匹配指定节点名。"""
    if not tag_filter:
        return _strip_decl(xml_text)
    root = ET.fromstring(xml_text)
    if scope is None:
        return " ".join(part.strip() for part in root.itertext() if part.strip())
    matched = [node for node in root.iter(scope)]
    if not matched:
        raise ValueError(f"未找到指定节点：{scope}")
    chunks = [" ".join(p.strip() for p in node.itertext() if p.strip()) for node in matched]
    return " ".join(chunk for chunk in chunks if chunk)


class XmlBodyExtractor(Operator):
    detection = "PTt_extract_xml_body"
    name = "XML抽出正文"
    tool_type = "规则型"
    version = "1.0.0"
    default_params = {"正文提取范围": "全文", "标签过滤": "启用", "属性过滤": "启用"}

    def _process_one(self, record: TextRecord, scope: Optional[str], tag_filter: bool) -> RecordResult:
        if record.metadata.get("decodeFailed"):
            return RecordResult(
                fieldName=record.record_id, tags=[TAG_UNPARSEABLE], action=ACTION_REMOVE,
                errorCode="DECODE_FAIL", error=record.metadata.get("parseError", "编码无法识别"),
                fields={"text": ""},
            )
        try:
            text = extract_xml_text(record.text, scope, tag_filter)
        except (ET.ParseError, ValueError) as exc:
            return RecordResult(
                fieldName=record.record_id, tags=[TAG_UNPARSEABLE], action=ACTION_REMOVE,
                errorCode="PARSE_FAIL", error=f"XML 解析失败：{exc}", fields={"text": ""},
            )
        return RecordResult(fieldName=record.record_id, action=ACTION_KEEP, fields={"text": text})

    def process(
        self,
        records: List[TextRecord],
        params: Optional[dict] = None,
        resources: Optional[dict] = None,
        context: Optional[OperatorContext] = None,
    ) -> OperatorOutput:
        merged = dict(self.default_params)
        merged.update(params or {})
        # 并发安全：参数局部化，经闭包传入（不落实例属性）
        scope_raw = str(merged.get("正文提取范围", "全文")).strip()
        scope = None if scope_raw in ("", "全文") else scope_raw
        tag_filter = parse_bool(merged.get("标签过滤", "启用"), default=True)

        def handle(record: TextRecord) -> RecordResult:
            return self._process_one(record, scope, tag_filter)

        return OperatorOutput(results=safe_map(records, handle, error_code="PARSE_FAIL"))


OPERATOR_CLASS = XmlBodyExtractor
