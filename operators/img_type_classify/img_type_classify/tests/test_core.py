"""img_type_classify 离线测试：大类一致性 / 低置信复核 / 枚举校验（模型调用 monkeypatch）。"""

import json
import sys
from pathlib import Path

import pytest
from PIL import Image

PKG_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PKG_ROOT))

from img_type_classify import operator as op  # noqa: E402
from img_type_classify.operator import run, validate_params  # noqa: E402
from img_type_classify.utils.llm_client import LlmError  # noqa: E402


def _noop_log(*args, **kwargs):
    pass


def _make_input(tmp_path, ids):
    input_dir = tmp_path / "in"
    (input_dir / "regions").mkdir(parents=True)
    records = []
    for iid in ids:
        Image.new("RGB", (100, 80), "white").save(input_dir / "regions" / f"{iid}.png")
        records.append({"imageId": iid, "fileName": f"{iid}.png", "image": f"regions/{iid}.png",
                        "region": {"bbox": [0, 0, 100, 80], "cropped": False,
                                   "width": 100, "height": 80, "sourceWidth": 100, "sourceHeight": 80}})
    with (input_dir / "records.jsonl").open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return input_dir


def _params():
    return validate_params({"category": "几何"})


def test_match_skip_review_branches(tmp_path, monkeypatch):
    mapping = {
        "img_a": {"match": True, "category": "几何", "subtype": "平面几何图", "confidence": 0.93, "reason": "有圆与标注"},
        "img_b": {"match": False, "category": "统计", "subtype": "折线图", "confidence": 0.95, "reason": "是折线图"},
        "img_c": {"match": True, "category": "几何", "subtype": "平面几何图", "confidence": 0.6, "reason": "拿不准"},
    }

    def _fake(system, user, image, **kwargs):
        iid = Path(str(image)).stem
        return json.dumps(mapping[iid], ensure_ascii=False)

    monkeypatch.setattr(op.llm_client, "chat_vision", _fake)
    result = run(_make_input(tmp_path, ["img_a", "img_b", "img_c"]), tmp_path / "out", _params(), _noop_log)
    assert result["summary"] == {"total": 3, "matched": 2, "skipped": 1, "review": 1, "failed": 0}
    assert "大类不一致" in result["skipped"][0]["reason"] and "实判=统计" in result["skipped"][0]["reason"]
    kept = [json.loads(l) for l in (tmp_path / "out" / "records.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [r["imageId"] for r in kept] == ["img_a", "img_c"]
    assert kept[0]["imageType"]["subtype"] == "平面几何图"
    assert "判型置信度低于阈值" in result["review"][0]["reviewReason"]


def test_enum_violation_retries_then_fails(tmp_path, monkeypatch):
    calls = {"n": 0}

    def _bad(system, user, image, **kwargs):
        calls["n"] += 1
        return json.dumps({"match": True, "category": "几何", "subtype": "立体几何图",
                           "confidence": 0.9, "reason": "x"})

    monkeypatch.setattr(op.llm_client, "chat_vision", _bad)
    result = run(_make_input(tmp_path, ["img_a"]), tmp_path / "out", _params(), _noop_log)
    assert calls["n"] == 2  # 输出非法重试 1 次
    assert result["summary"]["failed"] == 1 and "子类越枚举" in result["failed"][0]["reason"]


def test_model_failure_goes_failed(tmp_path, monkeypatch):
    def _boom(*a, **k):
        raise LlmError("HTTP 500")
    monkeypatch.setattr(op.llm_client, "chat_vision", _boom)
    result = run(_make_input(tmp_path, ["img_a"]), tmp_path / "out", _params(), _noop_log)
    assert result["summary"]["failed"] == 1 and result["summary"]["matched"] == 0


def test_category_required(tmp_path):
    with pytest.raises(ValueError, match="category"):
        validate_params({})
    with pytest.raises(ValueError, match="category"):
        validate_params({"category": "地图"})
