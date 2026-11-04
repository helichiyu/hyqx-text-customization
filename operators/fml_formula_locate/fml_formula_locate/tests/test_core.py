"""fml_formula_locate 离线测试：坐标校验 / 裁切 / 上下文截取 / 失败分支（模型调用 monkeypatch）。"""

import json
import sys
from pathlib import Path

import pymupdf
import pytest

PKG_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PKG_ROOT))

from fml_formula_locate import operator as op  # noqa: E402
from fml_formula_locate.operator import run, validate_params  # noqa: E402
from fml_formula_locate.utils.llm_client import LlmError  # noqa: E402


def _noop_log(*args, **kwargs):
    pass


def _make_pdf(path: Path, pages: int = 2) -> None:
    """造两页 PDF：每页一段正文 + 一个灰色矩形（充当公式区域），第 2 页无正文。"""
    font = "C:/Windows/Fonts/msyh.ttc"
    doc = pymupdf.open()
    for i in range(pages):
        page = doc.new_page(width=595, height=842)
        if i == 0:
            page.insert_text((72, 100), "第一章 极限 " * 8, fontsize=18,
                             fontfile=font, fontname="msyh")
            page.insert_text((72, 200), "本节介绍极限的基本定义。" * 6, fontsize=11,
                             fontfile=font, fontname="msyh")
            page.draw_rect(pymupdf.Rect(150, 300, 450, 340), fill=(0.9, 0.9, 0.9))
            page.insert_text((72, 420), "其中 a 为分子，b 为分母。" * 6, fontsize=11,
                             fontfile=font, fontname="msyh")
    path.write_bytes(doc.tobytes())
    doc.close()


def _input(tmp_path, name="sample.pdf", pages=2):
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    _make_pdf(input_dir / name, pages)
    return input_dir


def _fake_locate(system, user, image, **kwargs):
    page_no = int(str(image).rsplit("_p", 1)[1][:4])
    if page_no == 2:
        return json.dumps({"formulas": []})
    return json.dumps({"formulas": [
        {"bbox": [252, 356, 756, 403], "hasNumber": False, "confidence": 0.95},  # 矩形区域
        {"bbox": [0, 0, 3, 2], "hasNumber": False, "confidence": 0.9},            # 面积过小 → 跳过
        {"bbox": [-10, 100, 1200, 200], "hasNumber": False, "confidence": 0.9},   # 越界 → 跳过
    ]})


def test_locate_crop_context(tmp_path, monkeypatch):
    monkeypatch.setattr(op.llm_client, "chat_vision", _fake_locate)
    events = []
    result = run(_input(tmp_path), tmp_path / "out", validate_params({}), _noop_log,
                 progress=lambda **update: events.append(update))
    assert events[0]["total"] == 1 and events[0]["processed"] == 0
    assert events[-1] == {
        "total": 1, "processed": 1, "succeeded": 1, "skipped": 2, "failed": 0,
    }
    assert result["summary"]["located"] == 1 and result["summary"]["instances"] == 1
    assert result["summary"]["skipped"] == 2  # 两个非法 bbox
    rec = json.loads((tmp_path / "out" / "records.jsonl").read_text(encoding="utf-8").splitlines()[0])
    inst = rec["instances"][0]
    assert inst["pageNo"] == 1 and inst["bbox"] == [252, 356, 756, 403]
    assert (tmp_path / "out" / inst["crop"]).exists()
    assert "极限" in inst["contextText"] or "分子" in inst["contextText"]  # 上下文取到正文
    assert inst["chapterTitle"] and "极限" in inst["chapterTitle"]


def test_page_locate_failure_skipped(tmp_path, monkeypatch):
    def _fail(system, user, image, **kwargs):
        raise LlmError("HTTP 500")
    monkeypatch.setattr(op.llm_client, "chat_vision", _fail)
    result = run(_input(tmp_path), tmp_path / "out", validate_params({}), _noop_log)
    # 两页定位全失败 → 0 实例 → 整份失败（任务待处理口径）
    assert result["summary"]["located"] == 0 and result["summary"]["failed"] == 1
    assert result["failed"][0]["reason"] == "整份 0 个公式（未定位到公式）"
    assert sum("定位失败" in s["reason"] for s in result["skipped"]) == 2


def test_encrypted_goes_failed(tmp_path):
    samples = Path(__file__).resolve().parents[4] / "samples_pool" / "lay"
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    (input_dir / "encrypted.pdf").write_bytes((samples / "encrypted.pdf").read_bytes())
    result = run(input_dir, tmp_path / "out", validate_params({}), _noop_log)
    assert result["failed"] and "加密" in result["failed"][0]["reason"]


def test_valid_bbox():
    assert op._valid_bbox([0, 0, 100, 100]) == [0, 0, 100, 100]
    assert op._valid_bbox([10, 10, 5, 5]) is None      # x1>=x2
    assert op._valid_bbox([0, 0, 1001, 10]) is None    # 越界
    assert op._valid_bbox([0, 0, 4, 4]) is None        # 面积过小
    assert op._valid_bbox("bad") is None


def test_missing_input(tmp_path):
    result = run(tmp_path, tmp_path / "out", validate_params({}), _noop_log)
    assert result["summary"] == {"total": 0, "located": 0, "failed": 0, "instances": 0, "skipped": 0}
