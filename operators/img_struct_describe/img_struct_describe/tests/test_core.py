"""img_struct_describe 离线测试：4 类 Prompt 选择 / 字段校验 / 回核 / 三分低置信（模型 monkeypatch）。"""

import json
import sys
from pathlib import Path

import pytest
from PIL import Image

PKG_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PKG_ROOT))

from img_struct_describe import operator as op  # noqa: E402
from img_struct_describe.operator import run, validate_params  # noqa: E402
from img_struct_describe.utils.llm_client import LlmError  # noqa: E402


def _noop_log(*args, **kwargs):
    pass


def _rec(image_id, category, subtype, type_conf=0.9):
    return {"imageId": image_id, "fileName": f"{image_id}.png", "image": f"regions/{image_id}.png",
            "region": {"bbox": [0, 0, 100, 80], "cropped": False, "width": 100, "height": 80,
                       "sourceWidth": 100, "sourceHeight": 80},
            "imageType": {"match": True, "category": category, "subtype": subtype,
                          "confidence": type_conf, "reason": "x", "taskCategory": category}}


def _make_input(tmp_path, records):
    input_dir = tmp_path / "in"
    (input_dir / "regions").mkdir(parents=True)
    for rec in records:
        Image.new("RGB", (100, 80), "white").save(input_dir / rec["image"])
    with (input_dir / "records.jsonl").open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return input_dir


def _geo_payload(description=None, ocr=None):
    return {
        "type": "geometry", "subtype": "平面几何图",
        "ocr": ocr if ocr is not None else [{"text": "2√3", "conf": 0.9}],
        "description": description or {
            "图形类型": "平面几何图形", "基本构成": "半圆（直径 AB，圆心 O）",
            "辅助元素": "点 C 在弧上", "图形位置关系说明": "D 在 AB 上 O 左侧"},
        "fieldConfidence": {"图形类型": 0.95, "基本构成": 0.9, "辅助元素": 0.85, "图形位置关系说明": 0.9},
        "uncertain": [], "confidence": 0.9,
    }


def _payload_router(responses):
    def _fake(system, user, image, **kwargs):
        iid = Path(str(image)).stem
        payload = responses[iid]
        if isinstance(payload, Exception):
            raise payload
        return payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    return _fake


def test_geometry_clean_row(tmp_path, monkeypatch):
    monkeypatch.setattr(op.llm_client, "chat_vision", _payload_router({"g1": _geo_payload()}))
    result = run(_make_input(tmp_path, [_rec("g1", "几何", "平面几何图")]),
                 tmp_path / "out", validate_params({}), _noop_log)
    assert result["summary"] == {"total": 1, "described": 1, "review": 0, "failed": 0}
    row = json.loads((tmp_path / "out" / "records.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert row["type"] == "几何" and row["subtype"] == "平面几何图" and row["table"] is None
    assert row["confidence"] == {"type": 0.9, "ocr": 0.9, "desc": 0.85}  # desc=字段最低分（辅助元素 0.85）
    assert row["reviewStatus"] == "未进入复核" and row["lowConfidenceCount"] == 0


def test_missing_field_and_conf_goes_review(tmp_path, monkeypatch):
    payload = _geo_payload(description={"图形类型": "平面几何图形", "基本构成": "半圆",
                                        "图形位置关系说明": "无"})  # 缺"辅助元素"
    payload["fieldConfidence"] = {"图形类型": 0.9, "基本构成": 0.9, "图形位置关系说明": 0.9}  # 缺一个字段置信度
    monkeypatch.setattr(op.llm_client, "chat_vision", _payload_router({"g1": payload}))
    result = run(_make_input(tmp_path, [_rec("g1", "几何", "平面几何图")]),
                 tmp_path / "out", validate_params({}), _noop_log)
    reason = result["review"][0]["reviewReason"]
    assert "描述缺字段：辅助元素" in reason
    row = json.loads((tmp_path / "out" / "records.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert row["description"]["辅助元素"] == "无"


def test_number_verify_flags_unsupported(tmp_path, monkeypatch):
    payload = _geo_payload(description={
        "图形类型": "平面几何图形", "基本构成": "半圆，直径 8cm",  # 8 不在 OCR 里
        "辅助元素": "点 C 在弧上", "图形位置关系说明": "无"},
        ocr=[{"text": "2√3", "conf": 0.9}])
    monkeypatch.setattr(op.llm_client, "chat_vision", _payload_router({"g1": payload}))
    result = run(_make_input(tmp_path, [_rec("g1", "几何", "平面几何图")]),
                 tmp_path / "out", validate_params({}), _noop_log)
    assert "回核无依据内容" in result["review"][0]["reviewReason"]


def test_table_row_carries_table_struct(tmp_path, monkeypatch):
    payload = {
        "type": "table", "subtype": "三线表",
        "ocr": [{"text": "年份", "conf": 0.95}, {"text": "2023", "conf": 0.95}],
        "table": {"rows": 2, "cols": 2, "headerRows": [["年份", "营收"]],
                  "dataRows": [["2023", "120"]], "merges": []},
        "description": {"表格类型": "三线表", "表头": "年份、营收", "数据行": "2023 年 120 亿元", "备注": "无"},
        "fieldConfidence": {"表格类型": 0.95, "表头": 0.9, "数据行": 0.85, "备注": 0.8},
        "uncertain": [], "confidence": 0.9,
    }
    monkeypatch.setattr(op.llm_client, "chat_vision", _payload_router({"t1": payload}))
    result = run(_make_input(tmp_path, [_rec("t1", "表格", "三线表")]),
                 tmp_path / "out", validate_params({}), _noop_log)
    row = json.loads((tmp_path / "out" / "records.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert row["table"]["rows"] == 2 and row["table"]["headerRows"] == [["年份", "营收"]]


def test_subtype_mismatch_retries_then_fails(tmp_path, monkeypatch):
    calls = {"n": 0}

    def _wrong(system, user, image, **kwargs):
        calls["n"] += 1
        payload = _geo_payload()
        payload["subtype"] = "立体几何图"
        return json.dumps(payload, ensure_ascii=False)

    monkeypatch.setattr(op.llm_client, "chat_vision", _wrong)
    result = run(_make_input(tmp_path, [_rec("g1", "几何", "平面几何图")]),
                 tmp_path / "out", validate_params({}), _noop_log)
    assert calls["n"] == 2 and result["summary"]["failed"] == 1
    assert "与判型不符" in result["failed"][0]["reason"]


def test_low_type_confidence_flagged(tmp_path, monkeypatch):
    monkeypatch.setattr(op.llm_client, "chat_vision", _payload_router({"g1": _geo_payload()}))
    result = run(_make_input(tmp_path, [_rec("g1", "几何", "平面几何图", type_conf=0.6)]),
                 tmp_path / "out", validate_params({}), _noop_log)
    row = json.loads((tmp_path / "out" / "records.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert "判型偏低" in row["lowConfidenceReasons"] and row["lowConfidenceCount"] == 1


def test_missing_input_file(tmp_path):
    with pytest.raises(ValueError, match="records.jsonl"):
        run(tmp_path, tmp_path / "out", validate_params({}), _noop_log)
