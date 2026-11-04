"""HTML 正文抽取与清洗（纯标准库）。

抽取标题与块级正文段落，剔除 script/style；统计链接文字占比用于导航页判定。
编码兜底顺序：UTF-8 → GB18030（覆盖 GBK）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html import unescape
from html.parser import HTMLParser

BLOCK_TAGS = {
    "p", "div", "li", "td", "th", "section", "article",
    "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre",
}
SKIP_TAGS = {"script", "style", "noscript", "template"}
HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}

_WS_RE = re.compile(r"\s+")


@dataclass
class ExtractedDoc:
    title: str
    paragraphs: list[str] = field(default_factory=list)      # 清洗后的正文段落（含标题块）
    heading_flags: list[bool] = field(default_factory=list)  # 与 paragraphs 对齐：是否标题块
    total_chars: int = 0
    anchor_chars: int = 0

    @property
    def link_ratio(self) -> float:
        return self.anchor_chars / self.total_chars if self.total_chars else 0.0


class _Extractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._anchor_depth = 0
        self._in_title = False
        self._title_parts: list[str] = []
        self._buf: list[str] = []
        self._block_tag: str | None = None
        self.doc = ExtractedDoc(title="")

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in SKIP_TAGS:
            self._skip_depth += 1
        elif tag == "title":
            self._in_title = True
        elif tag == "a":
            self._anchor_depth += 1
        if self._skip_depth == 0 and tag in BLOCK_TAGS and self._block_tag is None:
            self._block_tag = tag
            self._buf = []

    def handle_endtag(self, tag: str) -> None:
        if tag in SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        elif tag == "title":
            self._in_title = False
        elif tag == "a" and self._anchor_depth > 0:
            self._anchor_depth -= 1
        if self._block_tag == tag:
            text = _WS_RE.sub(" ", unescape("".join(self._buf))).strip()
            if text:
                self.doc.paragraphs.append(text)
                self.doc.heading_flags.append(tag in HEADING_TAGS)
            self._block_tag = None
            self._buf = []

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        if self._in_title:
            self._title_parts.append(data.strip())
        if self._block_tag is not None:
            self._buf.append(data)
            n = len(data.strip())
            self.doc.total_chars += n
            if self._anchor_depth > 0:
                self.doc.anchor_chars += n

    def close(self) -> None:
        super().close()
        self.doc.title = _WS_RE.sub(" ", " ".join(self._title_parts)).strip()


def decode_html(raw: bytes) -> str:
    """按 UTF-8 → GB18030 顺序解码；都失败抛 ValueError。"""

    for enc in ("utf-8", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("编码不可识别（非 UTF-8 / GBK / GB18030）")


def extract(raw: bytes) -> ExtractedDoc:
    parser = _Extractor()
    parser.feed(decode_html(raw))
    parser.close()
    doc = parser.doc
    # <title> 缺失时回退到第一个标题块
    if not doc.title:
        for text, is_heading in zip(doc.paragraphs, doc.heading_flags):
            if is_heading:
                doc.title = text
                break
    return doc
