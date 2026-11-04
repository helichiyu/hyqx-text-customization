"""版面分页渲染 · 算子核心（复杂版面 环节①，纯规则不调模型）。

流程：打开 PDF（加密/损坏/0 页 → 失败清单）→ 逐页渲染（单页失败 → 失败页清单，不送环节②）
→ PageManifest（docId、pageCount、format、pageRange、checksum）→ 页图 + 页号交环节②。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pymupdf

from .configs import config
from .utils import pdf_utils
from .utils import review_codes
from .utils.pdf_utils import PdfError

OPERATOR_NAME = "版面分页渲染"
ALLOWED_SUFFIXES = (".pdf", ".zip")

PARAM_DEFAULTS: dict[str, Any] = {
    "dpi": config.RENDER_DPI,
    "image_format": config.IMAGE_FORMAT,
}

RECORDS_FILE = "records.jsonl"
PAGES_DIR = "pages"


def validate_params(params: dict[str, Any]) -> dict[str, Any]:
    merged = {**PARAM_DEFAULTS, **(params or {})}
    if not (72 <= int(merged["dpi"]) <= 300):
        raise ValueError("dpi 须在 72–300 之间（交付说明建议 150–200）")
    if merged["image_format"] not in ("png", "jpg", "jpeg"):
        raise ValueError("image_format 仅支持 png/jpg")
    return merged


def _render_page(page: pymupdf.Page, image_path: Path, matrix: pymupdf.Matrix) -> tuple[int, int]:
    """渲染单页，返回 (width, height)；独立成函数便于单页失败隔离。"""

    pix = page.get_pixmap(matrix=matrix)
    pix.save(image_path)
    return pix.width, pix.height


def _process_pdf(pdf_path: Path, output_dir: Path, dpi: int, image_format: str) -> dict[str, Any]:
    """单份 PDF：失败抛 PdfError；成功返回记录行（含失败页清单）。"""

    doc_id = pdf_path.stem
    manifest = pdf_utils.build_manifest(pdf_path, doc_id=doc_id)
    manifest["pageRange"] = [1, manifest["pageCount"]]

    pages_dir = output_dir / PAGES_DIR / doc_id
    pages_dir.mkdir(parents=True, exist_ok=True)
    matrix = pymupdf.Matrix(dpi / 72.0, dpi / 72.0)

    pages: list[dict[str, Any]] = []
    failed_pages: list[dict[str, Any]] = []
    with pdf_utils.open_pdf(pdf_path) as doc:
        for i in range(doc.page_count):
            page_no = i + 1
            image_path = pages_dir / f"{doc_id}_p{page_no:04d}.{image_format}"
            try:
                width, height = _render_page(doc.load_page(i), image_path, matrix)
            except Exception as e:
                failed_pages.append({"pageNo": page_no, "reason": f"渲染失败：{type(e).__name__}: {e}",
                                     "code": "page_render_failed"})
                continue
            pages.append({
                "pageNo": page_no,
                "image": str(image_path.relative_to(output_dir)),
                "width": width, "height": height,
            })
    if not pages:
        raise PdfError(f"全部页面渲染失败：{pdf_path.name}")
    return {
        "docId": doc_id, "fileName": pdf_path.name,
        "manifest": manifest, "pages": pages, "failedPages": failed_pages,
    }


def run(input_dir: Path, output_dir: Path, params: dict[str, Any], log) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in input_dir.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf")
    dpi = int(params["dpi"])
    image_format = str(params["image_format"])

    records: list[dict[str, Any]] = []
    failed: list[dict[str, str]] = []
    lineage: list[dict[str, Any]] = []

    for path in files:
        base = {"sample_id": path.stem, "source_file": path.name}
        try:
            record = _process_pdf(path, output_dir, dpi, image_format)
        except PdfError as e:
            msg = str(e)
            code = review_codes.pick(
                ("加密" in msg, "pdf_encrypted"),
                ("页数为 0" in msg, "pdf_empty"),
                ("损坏" in msg, "pdf_corrupt"),
                default="render_failed")
            failed.append({"name": path.name, "reason": msg, "code": code})
            lineage.append({**base, "action": "fail", "reason": msg})
            continue
        records.append(record)
        lineage.append({**base, "action": "keep",
                        "metrics": {"pages": len(record["pages"]), "failed_pages": len(record["failedPages"])}})

    with (output_dir / RECORDS_FILE).open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    total_pages = sum(len(r["pages"]) for r in records)
    total_failed_pages = sum(len(r["failedPages"]) for r in records)
    log("渲染完成：%d 份成功（%d 页），%d 份失败，失败页 %d 页",
        len(records), total_pages, len(failed), total_failed_pages)
    return {
        "records_file": RECORDS_FILE,
        "summary": {
            "total": len(files), "rendered": len(records), "failed": len(failed),
            "pages": total_pages, "failedPages": total_failed_pages,
        },
        "skipped": [],
        "failed": failed,
        "sample_lineage": lineage,
    }
