"""PTt_extract_doc_body：提取DOC正文（规则型，#7 清洗·正文）。

旧版二进制 .doc 提取迁移自 demo：镜像内 LibreOffice headless 转 txt。
- 魔数校验 D0CF11E0（OLE2 复合文档头）
- 本地/镜像无 LibreOffice 时给出明确报错（DOCX 无此依赖，走 #6）
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
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

_DOC_MAGIC = bytes.fromhex("D0CF11E0A1B11AE1")


def extract_doc_text(raw: bytes, filename: str) -> str:
    """LibreOffice headless 把 .doc 转为纯文本。"""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise RuntimeError("DOC 解析需要环境安装 LibreOffice（soffice）；DOCX 走 PTt_extract_docx_body 无此依赖")
    stem = os.path.splitext(os.path.basename(filename))[0] or "doc_input"
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / f"{stem}.doc"
        source.write_bytes(raw)
        result = subprocess.run(
            [soffice, "--headless", "--convert-to", "txt:Text", "--outdir", tmp, str(source)],
            check=False, capture_output=True, text=True, timeout=120,
        )
        target = Path(tmp) / f"{stem}.txt"
        if result.returncode != 0 or not target.is_file():
            raise ValueError(f"DOC 容器转换失败（损坏或非 DOC 文件）: {(result.stderr or '').strip()[:120]}")
        return target.read_text(encoding="utf-8", errors="replace")


class DocTextExtractor(Operator):
    detection = "PTt_extract_doc_body"
    name = "提取DOC正文"
    tool_type = "规则型"
    version = "1.0.0"
    default_params = {}

    def process(
        self,
        records: List,
        params: Optional[dict] = None,
        resources: Optional[dict] = None,
        context: Optional[OperatorContext] = None,
    ) -> OperatorOutput:
        raw = context.raw if context is not None else b""
        filename = (context.filename if context is not None else "") or ""
        stem = os.path.splitext(os.path.basename(filename))[0] or "record_0001"

        try:
            if not raw.startswith(_DOC_MAGIC):
                raise ValueError("非 DOC 输入或文件头不合法（本算子仅处理旧版 .doc 容器）")
            text = extract_doc_text(raw, filename)
            if not text.strip():
                raise ValueError("DOC 文件没有可提取正文")
            return OperatorOutput(results=[RecordResult(fieldName=stem, action=ACTION_KEEP, fields={"text": text})])
        except ValueError as exc:
            return OperatorOutput(results=[RecordResult(
                fieldName=stem, tags=[TAG_UNPARSEABLE], action=ACTION_REMOVE,
                errorCode="PARSE_FAIL", error=str(exc), fields={"text": ""},
            )])
        except Exception as exc:
            return OperatorOutput(results=[RecordResult(
                fieldName=stem, tags=[TAG_UNPARSEABLE], action=ACTION_REMOVE,
                errorCode="PARSE_FAIL", error=f"DOC 提取失败: {exc}", fields={"text": ""},
            )])


OPERATOR_CLASS = DocTextExtractor
