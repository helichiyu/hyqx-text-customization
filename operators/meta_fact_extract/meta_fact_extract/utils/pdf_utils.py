"""PDF 工具：逐页渲染、页清单、加密/损坏/0 页校验。

供 lay_page_render、fml_formula_locate 等算子核心使用（vendor 进内层包 utils/）。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import pymupdf


class PdfError(Exception):
    """PDF 不可用（加密/损坏/0 页），信息为中文。"""


@dataclass
class PageImage:
    page_no: int  # 从 1 开始
    image_path: Path
    width: int
    height: int


def sha256_of(path: Path, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while data := f.read(chunk):
            h.update(data)
    return h.hexdigest()


def open_pdf(pdf_path: str | Path) -> pymupdf.Document:
    """打开并校验 PDF；加密/损坏/0 页抛 PdfError。"""

    pdf_path = Path(pdf_path)
    try:
        doc = pymupdf.open(pdf_path)
    except Exception as e:
        raise PdfError(f"PDF 损坏或无法解析：{pdf_path.name}（{type(e).__name__}）") from e
    if doc.needs_pass or doc.is_encrypted:
        doc.close()
        raise PdfError(f"PDF 已加密：{pdf_path.name}")
    if doc.page_count <= 0:
        doc.close()
        raise PdfError(f"PDF 页数为 0：{pdf_path.name}")
    return doc


def render_pdf(
    pdf_path: str | Path,
    out_dir: str | Path,
    *,
    dpi: int = 150,
    image_format: str = "png",
) -> list[PageImage]:
    """逐页渲染为图片，返回页图清单（page_no 从 1 开始）。单页失败不中断，由调用方按缺失页号识别。"""

    pdf_path = Path(pdf_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pages: list[PageImage] = []
    with open_pdf(pdf_path) as doc:
        zoom = dpi / 72.0
        matrix = pymupdf.Matrix(zoom, zoom)
        for i in range(doc.page_count):
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=matrix)
            image_path = out_dir / f"{pdf_path.stem}_p{i + 1:04d}.{image_format}"
            pix.save(image_path)
            pages.append(PageImage(page_no=i + 1, image_path=image_path, width=pix.width, height=pix.height))
    return pages


def build_manifest(pdf_path: str | Path, *, doc_id: str | None = None) -> dict:
    """生成 PageManifest：docId、pageCount、format、checksum。"""

    pdf_path = Path(pdf_path)
    with open_pdf(pdf_path) as doc:
        page_count = doc.page_count
    return {
        "docId": doc_id or pdf_path.stem,
        "fileName": pdf_path.name,
        "pageCount": page_count,
        "format": pdf_path.suffix.lstrip(".").lower(),
        "checksum": sha256_of(pdf_path),
    }
