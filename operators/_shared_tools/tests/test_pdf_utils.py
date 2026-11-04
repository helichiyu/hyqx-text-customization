"""pdf_utils 单测：渲染、页清单、加密/损坏/0 页分支。"""

import sys
from pathlib import Path

import pymupdf
import pytest

SHARED = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SHARED))

from pdf_utils import PdfError, build_manifest, open_pdf, render_pdf  # noqa: E402


def _make_pdf(path: Path, pages: int = 2, encrypt: bool = False) -> Path:
    doc = pymupdf.open()
    for i in range(pages):
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), f"page {i + 1} hello")
    if encrypt:
        doc.save(path, encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="pw", owner_pw="pw")
    else:
        doc.save(path)
    doc.close()
    return path


def test_render_and_manifest(tmp_path):
    pdf = _make_pdf(tmp_path / "ok.pdf", pages=3)
    pages = render_pdf(pdf, tmp_path / "pages", dpi=150)
    assert len(pages) == 3
    assert pages[0].page_no == 1 and pages[0].image_path.exists()
    assert pages[0].width > 1000  # 150dpi 下 A4 宽约 1240px

    manifest = build_manifest(pdf, doc_id="d1")
    assert manifest["docId"] == "d1"
    assert manifest["pageCount"] == 3
    assert manifest["format"] == "pdf"
    assert len(manifest["checksum"]) == 64


def test_encrypted_rejected(tmp_path):
    pdf = _make_pdf(tmp_path / "enc.pdf", pages=1, encrypt=True)
    with pytest.raises(PdfError, match="加密"):
        open_pdf(pdf)


def test_corrupt_rejected(tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not a pdf at all")
    with pytest.raises(PdfError, match="损坏"):
        open_pdf(bad)


def test_zero_page_rejected(tmp_path):
    # pymupdf 不允许保存 0 页文档，手工拼一个页数为 0 的最小合法 PDF
    raw = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [] /Count 0 >> endobj\n"
        b"trailer << /Root 1 0 R >>\n"
    )
    empty = tmp_path / "empty.pdf"
    empty.write_bytes(raw)
    with pytest.raises(PdfError, match="页数为 0"):
        open_pdf(empty)
