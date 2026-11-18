"""PTt_extract_pdf_body：提取PDF正文（小模型，#5 清洗·正文）。

文本层提取迁移自 demo（pypdf）；页码范围参数为本版新增。
- param_页码范围：全部（默认）/ "1-3" / "2,5"
- param_表格提取 / param_图片文字提取：记录口径，pypdf 文本层不区分（见 README 限制说明）
- param_OCR识别（默认启用）：无文本层的扫描版 PDF 走 OCR 兜底——
  Qwen3-VL-8B-Instruct（硅基流动 API，与内部自部署同款，2026-11 换型：
  PaddleOCR-VL 华为平台无法部署）；设为"关闭"则扫描版明确报错拦截
- 提取方式在 fields.extractionMethod 标注（text-layer / ocr(qwen3-vl)）
"""

from __future__ import annotations

import os
import re
from typing import List, Optional

from common.operator_base import (
    ACTION_KEEP,
    ACTION_REMOVE,
    Operator,
    OperatorContext,
    OperatorOutput,
    RecordResult,
    TAG_UNPARSEABLE,
)

_PAGE_RANGE_RE = re.compile(r"^[\d,\-]+$")


def parse_page_range(spec: str, total: int) -> List[int]:
    """解析页码范围（1-based，闭区间）：全部 / 1-3 / 2,5 → 0-based 页索引列表。"""
    spec = (spec or "全部").strip()
    if spec in ("", "全部", "all", "All"):
        return list(range(total))
    if not _PAGE_RANGE_RE.match(spec):
        raise ValueError(f"页码范围格式非法: {spec!r}（应为 全部 / 1-3 / 2,5）")
    pages: List[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, _, end = part.partition("-")
            start_i, end_i = int(start), int(end)
            if start_i < 1 or end_i < start_i:
                raise ValueError(f"页码范围非法: {part}（应为 1 ≤ 起 ≤ 止）")
            pages.extend(range(start_i - 1, min(end_i, total)))
        else:
            index = int(part) - 1
            if index < 0:
                raise ValueError(f"页码非法: {part}")
            if index < total:
                pages.append(index)
    if not pages:
        raise ValueError(f"页码范围 {spec} 超出文档页数（共 {total} 页）")
    return sorted(set(pages))


def extract_pdf_pages(raw: bytes, page_indexes: Optional[List[int]]) -> tuple:
    """提取 PDF 文本层。返回 (文本, 页数, 总页数)。"""
    from pypdf import PdfReader

    reader = PdfReader(raw and __import__("io").BytesIO(raw) or None)
    total = len(reader.pages)
    indexes = page_indexes if page_indexes is not None else list(range(total))
    texts = []
    for index in indexes:
        try:
            page_text = reader.pages[index].extract_text() or ""
        except Exception:  # 单页提取失败不中断整批
            page_text = ""
        if page_text.strip():
            texts.append(page_text.strip())
    return "\n\n".join(texts), len(indexes), total


class PdfTextExtractor(Operator):
    detection = "PTt_extract_pdf_body"
    name = "提取PDF正文"
    tool_type = "小模型"
    version = "1.1.0"
    default_params = {"页码范围": "全部", "表格提取": "启用", "图片文字提取": "启用", "OCR识别": "启用"}

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
            if not raw.startswith(b"%PDF"):
                raise ValueError("非 PDF 输入或文件头不合法（本算子仅处理 PDF 容器）")
            page_spec = str(merged.get("页码范围", "全部"))
            # 先读总页数再解析范围
            from pypdf import PdfReader

            total = len(PdfReader(__import__("io").BytesIO(raw)).pages)
            indexes = parse_page_range(page_spec, total)
            text, used, _total = extract_pdf_pages(raw, indexes)

            if not text.strip():
                # 扫描版 PDF：OCR 兜底（Qwen3-VL-8B-Instruct，硅基流动 API——
                # 与内部自部署同款，2026-11 换型；PaddleOCR-VL 华为平台无法部署）
                ocr_enabled = str(merged.get("OCR识别", "启用")) != "关闭"
                if not ocr_enabled:
                    raise ValueError("PDF 不包含可提取的文本层（扫描版），且 param_OCR识别=关闭")
                from common.ocr import ocr_pdf

                text, used = ocr_pdf(raw, indexes)
                if not text.strip():
                    raise ValueError("OCR 未从扫描页中提取到文字（页面可能为纯图形）")
                return OperatorOutput(results=[RecordResult(
                    fieldName=stem, action=ACTION_KEEP,
                    fields={"text": text, "pages": used, "extractionMethod": "ocr(qwen3-vl)"},
                )])
            return OperatorOutput(results=[RecordResult(
                fieldName=stem, action=ACTION_KEEP,
                fields={"text": text, "pages": used, "extractionMethod": "text-layer"},
            )])
        except ValueError as exc:
            return OperatorOutput(results=[RecordResult(
                fieldName=stem, tags=[TAG_UNPARSEABLE], action=ACTION_REMOVE,
                errorCode="PARSE_FAIL", error=str(exc), fields={"text": ""},
            )])
        except Exception as exc:  # pypdf 解析异常（损坏/加密）统一转干净报错
            return OperatorOutput(results=[RecordResult(
                fieldName=stem, tags=[TAG_UNPARSEABLE], action=ACTION_REMOVE,
                errorCode="PARSE_FAIL",
                error=f"PDF 容器无法解析（损坏、非 PDF 或加密）: {exc}", fields={"text": ""},
            )])


OPERATOR_CLASS = PdfTextExtractor
