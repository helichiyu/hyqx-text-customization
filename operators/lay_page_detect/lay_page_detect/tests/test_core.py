"""lay_page_detect 离线测试：六类分流规则 / 后处理校验 / 失败页（模型调用 monkeypatch）。"""

import json
import sys
from pathlib import Path

import pytest
from PIL import Image

PKG_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PKG_ROOT))

from lay_page_detect import operator as op  # noqa: E402
from lay_page_detect.operator import run, validate_params  # noqa: E402
from lay_page_detect.utils.llm_client import LlmError  # noqa: E402


def _noop_log(*args, **kwargs):
    pass


def _elem(eid, type_="body", bbox=(100, 100, 300, 300), order=1, bc=0.9, tc=0.9):
    return {"elementId": eid, "type": type_, "bbox": list(bbox),
            "readingOrder": order, "bboxConf": bc, "typeConf": tc}


def _make_input(tmp_path, page_count=8, render_failed=None):
    """伪造 lay_page_render 产物：records.jsonl + 8 张页图。"""
    input_dir = tmp_path / "in"
    pages_dir = input_dir / "pages" / "doc1"
    pages_dir.mkdir(parents=True)
    pages = []
    for i in range(1, page_count + 1):
        img = pages_dir / f"doc1_p{i:04d}.png"
        Image.new("RGB", (200, 280), "white").save(img)
        pages.append({"pageNo": i, "image": f"pages/doc1/doc1_p{i:04d}.png", "width": 200, "height": 280})
    rec = {
        "docId": "doc1", "fileName": "doc1.pdf",
        "manifest": {"docId": "doc1", "pageCount": page_count, "format": "pdf",
                     "pageRange": [1, page_count], "checksum": "x" * 64},
        "pages": pages, "failedPages": render_failed or [],
    }
    with (input_dir / "records.jsonl").open("w", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return input_dir


# 各页模型输出：1 干净 / 2 框选偏低 / 3 判定偏低 / 4 重叠 / 5 越界 / 6 顺序重号 / 7 空页 / 8 调用失败
PAGE_OUTPUTS = {
    1: {"pageNo": 1, "elements": [_elem("e1", "header", (10, 10, 900, 50), 1),
                                  _elem("e2", "body", (10, 100, 490, 900), 2)],
        "structureTree": [{"id": "e1", "children": []}]},
    2: {"pageNo": 2, "elements": [_elem("e1", "body", (10, 100, 490, 900), 1, bc=0.6)], "structureTree": []},
    3: {"pageNo": 3, "elements": [_elem("e1", "body", (10, 100, 490, 900), 1, tc=0.5)], "structureTree": []},
    4: {"pageNo": 4, "elements": [_elem("e1", "body", (10, 100, 500, 500), 1),
                                  _elem("e2", "figure", (20, 110, 490, 490), 2)], "structureTree": []},
    5: {"pageNo": 5, "elements": [_elem("e1", "body", (-50, 100, 1200, 900), 1)], "structureTree": []},
    6: {"pageNo": 6, "elements": [_elem("e1", "body", (10, 100, 490, 500), 1),
                                  _elem("e2", "body", (10, 510, 490, 900), 1)], "structureTree": []},
    7: {"pageNo": 7, "elements": [], "structureTree": []},
}


def _fake_chat_vision(system, user, image, **kwargs):
    page_no = int(str(image).rsplit("_p", 1)[1][:4])
    if page_no == 8:
        raise LlmError("HTTP 500")
    return json.dumps(PAGE_OUTPUTS[page_no], ensure_ascii=False)


def test_six_rules_and_failed_page(tmp_path, monkeypatch):
    monkeypatch.setattr(op.llm_client, "chat_vision", _fake_chat_vision)
    input_dir = _make_input(tmp_path, render_failed=[{"pageNo": 9, "reason": "渲染失败：mock"}])
    result = run(input_dir, tmp_path / "out", validate_params({}), _noop_log)

    assert result["summary"] == {"docs": 1, "pages": 8, "detected": 7, "review": 6, "failedPages": 2}
    rows = {r["pageNo"]: r for r in
            (json.loads(l) for l in (tmp_path / "out" / "records.jsonl").read_text(encoding="utf-8").splitlines())}
    assert rows[1]["reviewStatus"] == "未进入复核" and rows[1]["revisionStatus"] == "—"
    assert "框选偏低" in rows[2]["lowConfidenceReasons"]
    assert "判定偏低" in rows[3]["lowConfidenceReasons"]
    assert "重叠" in rows[4]["lowConfidenceReasons"]
    assert "越界" in rows[5]["lowConfidenceReasons"]
    assert rows[5]["elements"][0]["bbox"] == [0, 100, 1000, 900]  # 截断修正
    assert "顺序冲突" in rows[6]["lowConfidenceReasons"]
    assert rows[7]["lowConfidenceReasons"] == "空页"
    # 复核文件 6 页，失败页 2 页（模型失败 + 渲染失败汇入）
    review = (tmp_path / "out" / "review.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(review) == 6
    names = {f["name"] for f in result["failed"]}
    assert names == {"doc1-#8", "doc1-#9"}
    # 框选图层已生成
    assert (tmp_path / "out" / "visual" / "doc1_p0001.png").exists()


def test_pageno_mismatch_retries_then_fails(tmp_path, monkeypatch):
    calls = {"n": 0}

    def _wrong_page(system, user, image, **kwargs):
        calls["n"] += 1
        return json.dumps({"pageNo": 99, "elements": [], "structureTree": []})

    monkeypatch.setattr(op.llm_client, "chat_vision", _wrong_page)
    input_dir = _make_input(tmp_path, page_count=1)
    result = run(input_dir, tmp_path / "out", validate_params({}), _noop_log)
    assert calls["n"] == 2  # 输出非法重试 1 次
    assert result["summary"]["detected"] == 0 and result["summary"]["failedPages"] == 1
    assert "pageNo 不一致" in result["failed"][0]["reason"]


def test_iou():
    assert op._iou([0, 0, 100, 100], [50, 50, 150, 150]) == pytest.approx(2500 / 17500)
    assert op._iou([0, 0, 100, 100], [200, 200, 300, 300]) == 0.0


def test_missing_input_file(tmp_path):
    with pytest.raises(ValueError, match="records.jsonl"):
        run(tmp_path, tmp_path / "out", validate_params({}), _noop_log)
