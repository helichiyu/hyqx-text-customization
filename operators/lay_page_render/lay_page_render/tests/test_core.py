"""lay_page_render 离线测试：渲染 + PageManifest + 加密/损坏/0 页/单页失败分支。"""

import json
import sys
from pathlib import Path

import pytest

PKG_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PKG_ROOT))

from lay_page_render import operator as op  # noqa: E402
from lay_page_render.operator import run, validate_params  # noqa: E402

SAMPLES = Path(__file__).resolve().parents[4] / "samples_pool" / "lay"
ZERO_PAGE_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)


def _noop_log(*args, **kwargs):
    pass


def _input(tmp_path, *names):
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    for name in names:
        (input_dir / name).write_bytes((SAMPLES / name).read_bytes())
    return input_dir


def test_render_and_manifest(tmp_path):
    result = run(_input(tmp_path, "layout_sample.pdf"), tmp_path / "out", validate_params({}), _noop_log)
    assert result["summary"]["rendered"] == 1 and result["summary"]["pages"] == 3
    rec = json.loads((tmp_path / "out" / "records.jsonl").read_text(encoding="utf-8").splitlines()[0])
    m = rec["manifest"]
    assert m["pageCount"] == 3 and m["format"] == "pdf" and m["pageRange"] == [1, 3] and len(m["checksum"]) == 64
    for p in rec["pages"]:
        img = tmp_path / "out" / p["image"]
        assert img.exists() and p["width"] > 0 and p["height"] > 0
    assert rec["failedPages"] == []


def test_encrypted_goes_failed(tmp_path):
    result = run(_input(tmp_path, "encrypted.pdf"), tmp_path / "out", validate_params({}), _noop_log)
    assert result["summary"] == {"total": 1, "rendered": 0, "failed": 1, "pages": 0, "failedPages": 0}
    assert "加密" in result["failed"][0]["reason"]


def test_corrupt_and_zero_page_go_failed(tmp_path):
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    (input_dir / "corrupt.pdf").write_bytes(b"not a pdf at all")
    (input_dir / "zero.pdf").write_bytes(ZERO_PAGE_PDF)
    result = run(input_dir, tmp_path / "out", validate_params({}), _noop_log)
    reasons = {f["name"]: f["reason"] for f in result["failed"]}
    assert "损坏" in reasons["corrupt.pdf"]
    assert "页数为 0" in reasons["zero.pdf"]


def test_single_page_failure_isolated(tmp_path, monkeypatch):
    """单页渲染失败 → 失败页清单，其余页照常。"""
    original = op._render_page

    def _flaky(page, image_path, matrix):
        if page.number == 1:  # 第 2 页失败
            raise RuntimeError("mock render boom")
        return original(page, image_path, matrix)

    monkeypatch.setattr(op, "_render_page", _flaky)
    result = run(_input(tmp_path, "layout_sample.pdf"), tmp_path / "out", validate_params({}), _noop_log)
    rec = json.loads((tmp_path / "out" / "records.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert [p["pageNo"] for p in rec["pages"]] == [1, 3]
    assert rec["failedPages"][0]["pageNo"] == 2 and "渲染失败" in rec["failedPages"][0]["reason"]
    assert result["summary"]["failedPages"] == 1


def test_all_pages_fail_goes_failed(tmp_path, monkeypatch):
    monkeypatch.setattr(op, "_render_page", lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))
    result = run(_input(tmp_path, "layout_sample.pdf"), tmp_path / "out", validate_params({}), _noop_log)
    assert result["summary"]["rendered"] == 0 and result["summary"]["failed"] == 1
    assert "全部页面渲染失败" in result["failed"][0]["reason"]


def test_params_validation():
    with pytest.raises(ValueError, match="dpi"):
        validate_params({"dpi": 50})
    with pytest.raises(ValueError, match="image_format"):
        validate_params({"image_format": "tiff"})
