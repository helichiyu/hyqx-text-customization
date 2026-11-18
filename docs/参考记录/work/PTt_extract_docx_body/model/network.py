"""PTt_extract_docx_body：提取DOCX正文（规则型，#6 清洗·正文）。

段落+表格提取迁移自 demo（python-docx），按 Excel 配置项补齐参数：
- param_表格内容：保留（默认）/ 删除 —— 表格行是否进入正文
- param_批注：删除（默认）/ 保留 —— 保留时批注以 【批注】x 形式附加段尾
- param_超链接：删除（默认）/ 保留 —— 保留时经 XML 层取 w:t（含超链接 run 文本）
- param_图片说明文字：保留（默认）—— 图片题注本身是普通段落，天然保留，仅记录口径

输入为二进制 docx（context.raw），魔数 PK 校验。
"""

from __future__ import annotations

import os
from typing import List, Optional

from common.operator_base import (
    ACTION_KEEP,
    ACTION_REMOVE,
    Operator,
    OperatorContext,
    OperatorOutput,
    RecordResult,
    TAG_UNPARSEABLE,
    parse_bool,
)


def extract_docx_text(raw: bytes, keep_tables: bool, keep_comments: bool, keep_hyperlinks: bool) -> str:
    from docx import Document
    import io

    document = Document(io.BytesIO(raw))

    def para_text(paragraph) -> str:
        if keep_hyperlinks:
            # paragraph.text 不含 w:hyperlink 内的 run；保留超链接时走 XML 层取全部 w:t
            nodes = paragraph._element.xpath(".//w:t")
            return "".join(node.text or "" for node in nodes).strip()
        return paragraph.text.strip()

    parts = [para_text(p) for p in document.paragraphs]
    parts = [part for part in parts if part]

    if keep_tables:
        for table in document.tables:
            for row in table.rows:
                values = [cell.text.strip() for cell in row.cells]
                if any(values):
                    parts.append(" | ".join(values))

    if keep_comments:
        comments = getattr(document, "comments", None)
        if comments:
            for comment in comments:
                author = getattr(comment, "author", "") or "批注者"
                # python-docx 各版本 Comment 形态不一：优先 .text 属性，
                # 无该属性再走段落 XML 提取，两者皆失败则跳过该条批注
                text = ""
                text_attr = getattr(comment, "text", None)
                if isinstance(text_attr, str):
                    text = text_attr.strip()
                else:
                    try:
                        paragraphs = getattr(comment, "paragraphs", []) or []
                        text = "".join(
                            node.text or "" for p in paragraphs
                            for node in p._element.xpath(".//w:t")
                        ).strip()
                    except Exception:  # noqa: BLE001 - 批注提取失败不影响正文
                        continue
                if text:
                    parts.append(f"【批注·{author}】{text}")

    return "\n".join(parts)


class DocxTextExtractor(Operator):
    detection = "PTt_extract_docx_body"
    name = "提取DOCX正文"
    tool_type = "规则型"
    version = "1.0.0"
    default_params = {"表格内容": "保留", "批注": "删除", "超链接": "删除", "图片说明文字": "保留"}

    def process(
        self,
        records: List,
        params: Optional[dict] = None,
        resources: Optional[dict] = None,
        context: Optional[OperatorContext] = None,
    ) -> OperatorOutput:
        merged = dict(self.default_params)
        merged.update(params or {})
        raw = context.raw if context is not None else b""
        filename = (context.filename if context is not None else "") or ""
        stem = os.path.splitext(os.path.basename(filename))[0] or "record_0001"

        try:
            if not raw.startswith(b"PK"):
                raise ValueError("非 DOCX 输入或文件头不合法（本算子仅处理 .docx 容器）")
            text = extract_docx_text(
                raw,
                keep_tables=parse_bool(merged.get("表格内容", "保留"), default=True),
                keep_comments=parse_bool(merged.get("批注", "删除"), default=False),
                keep_hyperlinks=parse_bool(merged.get("超链接", "删除"), default=False),
            )
            if not text.strip():
                raise ValueError("DOCX 文件没有可提取正文")
            return OperatorOutput(results=[RecordResult(fieldName=stem, action=ACTION_KEEP, fields={"text": text})])
        except ValueError as exc:
            return OperatorOutput(results=[RecordResult(
                fieldName=stem, tags=[TAG_UNPARSEABLE], action=ACTION_REMOVE,
                errorCode="PARSE_FAIL", error=str(exc), fields={"text": ""},
            )])
        except Exception as exc:  # 非 DOCX 容器/损坏 zip 统一转干净报错
            return OperatorOutput(results=[RecordResult(
                fieldName=stem, tags=[TAG_UNPARSEABLE], action=ACTION_REMOVE,
                errorCode="PARSE_FAIL", error=f"DOCX 容器无法解析（损坏或非 DOCX 文件）: {exc}",
                fields={"text": ""},
            )])


OPERATOR_CLASS = DocxTextExtractor
