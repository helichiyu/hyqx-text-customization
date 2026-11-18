"""PTt_extract_html_body：提取HTML/网页正文（规则型）。

核心算法迁移自 pretrain_text_service_demo（A 级复用），适配本组处理器接口：
- 行块分布函数定位正文区：正文行显著长于导航行，滑窗求行块长度后取密度平台段
- 两端剔除短小 UI 行（登录/注册/分享等），保留正文内部短句
- 404/失效页检测：命中即按"提取失败"口径打标（主表拦截处理：原始文件-无法解析 → 隔离）

接口契约见 docs/预训练文本算子开发规范-V1.0.md 第 3~5 章。
"""

from __future__ import annotations

import html
import re
from typing import List, Optional, Tuple

from common.operator_base import (
    ACTION_KEEP,
    ACTION_REMOVE,
    Operator,
    OperatorOutput,
    RecordResult,
    TAG_UNPARSEABLE,
    TextRecord,
    safe_map,
)

TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_STYLE_RE = re.compile(r"<(script|style|noscript)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
DOCTYPE_RE = re.compile(r"<!DOCTYPE[^>]*>", re.IGNORECASE)

# 行块密度参数：窗口 3 行，正文平台判定为峰值密度的 35%。
_BLOCK_WINDOW = 3
_DENSITY_RATIO = 0.35
_MIN_LINES_FOR_DETECTION = 8
# 两端 UI 行判据：短且不含任何标点（正文短句通常带标点），
# 或短行以常见 UI 动词开头（点击播报/分享/打印等，实测新闻页头部残留）。
_CHROME_MAX_LEN = 12
_CHROME_UI_MAX_LEN = 20
_UI_START_RE = re.compile(
    r"^(点击|播报|分享|收藏|打印|举报|关注我们|订阅|展开|收起|阅读全文|更多|相关推荐|猜你喜欢)"
)
_PUNCT_RE = re.compile(r"[。，、；：？！.,;:?!]")

# 错误页特征：**行级**匹配（整行是错误提示横幅）——不得子串搜索，
# 否则正文提及"404/not found"的技术文章会被整篇误杀（自检实证）。
# 真实错误页的特征是独立短行；正文里这些词总伴随长句上下文。
_ERROR_LINE_PATTERNS = [
    re.compile(r"^[\s\[（(【!！]*404(?:\s*(?:not\s*found|错误|页面|page))?[\s\]）)】.。!！]*$", re.IGNORECASE),
    re.compile(r"^[\s\[（(【!！]*(?:page\s+)?not\s*found[\s\]）)】.。!！]*$", re.IGNORECASE),
    re.compile(r"^[\s，。、！!]*(?:页面不存在|页面未找到|链接已失效|您?访问的页面[^。]{0,6})[\s。！!]*$"),
    re.compile(r"^抱歉[^。]{0,12}(?:没有找到|找不到|未找到)[\s。！!]*$"),
]
_ERROR_HEAD_LINES = 15
_ERROR_LINE_MAX_LEN = 40   # 横幅行长度上限——超过即为正文句


def _looks_like_chrome(line: str) -> bool:
    if len(line) <= _CHROME_MAX_LEN and not _PUNCT_RE.search(line):
        return True
    return len(line) <= _CHROME_UI_MAX_LEN and bool(_UI_START_RE.match(line))


# 站点导航/页脚高频词：密度区间内部出现时精确剔除（仅整行命中词表才删，
# 不做短行一刀切，避免误伤"上证指数"这类正文短行）。实测 chinanews/cnblogs
# 残留样本：'关于我们'、'注册'、'首页'、'订阅' 均为词表独立行。
_CHROME_LINE_WORDS = {
    "首页", "网站首页", "登录", "登入", "注册", "注销", "订阅", "关注我们",
    "关于我们", "联系我们", "联系方式", "友情链接", "站点地图", "网站地图",
    "意见反馈", "使用条款", "隐私政策", "免责声明", "版权所有", "返回顶部",
    "相关新闻", "相关推荐", "热门推荐", "猜你喜欢", "点击查看更多", "展开",
    "收起", "更多", "分享", "收藏", "打印", "举报", "赞赏",
    "退出登录", "立即登录", "马上登录", "忘记密码", "点击登录",
}
_CHROME_SPLIT_RE = re.compile(r"[|｜/·>»\s—\-]+")
# "版权所有:东方财富网" 类站点署名行（版权/免责声明 + 冒号 + 站名，≤20字）
_COPYRIGHT_LINE_RE = re.compile(
    r"^(版权所有|免责声明|Copyright)[：:]?\s*[一-龥A-Za-z0-9]{0,20}$", re.IGNORECASE
)


def _is_chrome_vocab_line(line: str) -> bool:
    """整行均由导航/页脚词表词条组成（支持 '首页 | 新闻 | 注册' 与 '注册登录' 组合）。"""
    stripped = line.strip()
    if _COPYRIGHT_LINE_RE.match(stripped):
        return True
    tokens = [t for t in _CHROME_SPLIT_RE.split(stripped) if t]
    if not tokens:
        return False
    if all(token in _CHROME_LINE_WORDS for token in tokens):
        return True
    # 短行二词组合：'注册登录' = 注册 + 登录
    if len(tokens) == 1 and len(tokens[0]) <= 8:
        word = tokens[0]
        for cut in range(1, len(word)):
            if word[:cut] in _CHROME_LINE_WORDS and word[cut:] in _CHROME_LINE_WORDS:
                return True
    return False


def _strip_interior_chrome(lines: List[str]) -> List[str]:
    return [line for line in lines if not _is_chrome_vocab_line(line)]


def _is_error_page(lines: List[str]) -> bool:
    for line in lines[:_ERROR_HEAD_LINES]:
        stripped = line.strip()
        if not stripped or len(stripped) > _ERROR_LINE_MAX_LEN:
            continue
        if any(p.match(stripped) for p in _ERROR_LINE_PATTERNS):
            return True
    return False


def _trim_chrome_edges(lines: List[str]) -> List[str]:
    """两端向内剔除 UI 行；保留正文内部的短句。"""
    start, end = 0, len(lines)
    while start < end and _looks_like_chrome(lines[start]):
        start += 1
    while end > start and _looks_like_chrome(lines[end - 1]):
        end -= 1
    return lines[start:end] if end > start else []


def _extract_body_region(lines: List[str]) -> List[str]:
    """按行块密度定位正文平台段；短文本跳过密度检测但仍剔除边缘 UI 行。

    密度区间内的独立导航/页脚词行（demo 评估中 18.9% 文件残留的根因）一并剔除。
    """
    if len(lines) < _MIN_LINES_FOR_DETECTION:
        return _strip_interior_chrome(_trim_chrome_edges(lines))
    lengths = [len(line) for line in lines]
    blocks = [
        sum(lengths[i : i + _BLOCK_WINDOW])
        for i in range(len(lengths) - _BLOCK_WINDOW + 1)
    ]
    peak = max(blocks) if blocks else 0
    if peak <= 0:
        return lines
    threshold = peak * _DENSITY_RATIO
    hit = [i for i, value in enumerate(blocks) if value >= threshold]
    if not hit:
        return lines
    start, end = hit[0], min(len(lines), hit[-1] + _BLOCK_WINDOW)
    return _strip_interior_chrome(_trim_chrome_edges(lines[start:end]))


def strip_to_lines(raw_html: str) -> List[str]:
    """剥标签/脚本/注释，反转义实体，行内空白归一，去空行。"""
    text = SCRIPT_STYLE_RE.sub("\n", raw_html)
    text = COMMENT_RE.sub("\n", text)
    text = html.unescape(DOCTYPE_RE.sub("\n", TAG_RE.sub("\n", text)))
    lines = [re.sub(r"[ \t]+", " ", line.strip()) for line in text.splitlines()]
    return [line for line in lines if line]


def extract_body(raw_html: str) -> Tuple[str, bool]:
    """提取正文。返回 (正文, 是否错误页)。"""
    lines = strip_to_lines(raw_html)
    if lines and _is_error_page(lines):
        return "", True
    return "\n".join(_extract_body_region(lines)), False


class HtmlBodyExtractor(Operator):
    detection = "PTt_extract_html_body"
    name = "提取HTML/网页正文"
    tool_type = "规则型"
    version = "1.0.0"
    default_params = {}  # 主表配置项列无算子侧参数（"--"）

    def _process_one(self, record: TextRecord) -> RecordResult:
        if record.metadata.get("decodeFailed"):
            # 编码无法解码：本算子口径 = 提取失败（编码拦截是 #2/#10 的职责）
            return RecordResult(
                fieldName=record.record_id,
                tags=[TAG_UNPARSEABLE],
                action=ACTION_REMOVE,
                errorCode="DECODE_FAIL",
                error=record.metadata.get("parseError", "编码无法识别"),
                fields={"text": ""},
            )
        if record.metadata.get("parseError") and not record.text.strip():
            return RecordResult(
                fieldName=record.record_id,
                tags=[TAG_UNPARSEABLE],
                action=ACTION_REMOVE,
                errorCode="PARSE_FAIL",
                error=record.metadata["parseError"],
                fields={"text": ""},
            )
        body, is_error_page = extract_body(record.text)
        if is_error_page:
            return RecordResult(
                fieldName=record.record_id,
                tags=[TAG_UNPARSEABLE],
                action=ACTION_REMOVE,
                fields={"text": "", "reason": "404/失效页面，无有效正文"},
            )
        return RecordResult(fieldName=record.record_id, action=ACTION_KEEP, fields={"text": body})

    def process(
        self,
        records: List[TextRecord],
        params: Optional[dict] = None,
        resources: Optional[dict] = None,
        context=None,
    ) -> OperatorOutput:
        return OperatorOutput(results=safe_map(records, self._process_one, error_code="PARSE_FAIL"))


OPERATOR_CLASS = HtmlBodyExtractor
