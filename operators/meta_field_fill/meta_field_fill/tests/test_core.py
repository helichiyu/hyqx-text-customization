"""meta_field_fill 离线测试：16 字段校验 / 数据集行格式 / 分流（模型调用 monkeypatch）。"""

import json
import sys
from pathlib import Path

import pytest

PKG_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PKG_ROOT))

from meta_field_fill import operator as op  # noqa: E402
from meta_field_fill.configs import config  # noqa: E402
from meta_field_fill.operator import run, validate_params  # noqa: E402


def _noop_log(*args, **kwargs):
    pass


def _record(doc_id):
    return {
        "docId": doc_id, "fileName": f"{doc_id}.html", "title": f"{doc_id}标题",
        "textLength": 100, "sliceCount": 1,
        "slices": [{"sliceId": f"{doc_id}-s01", "index": 1, "text": "正文内容" * 20, "charCount": 80}],
        "facts": {
            "sourceType": {"value": "官方媒体", "confidence": 0.9},
            "timeCandidates": [{"value": "2021 年 6 月", "confidence": 0.9}],
            "entities": [{"mention": "张伟", "kind": "person", "confidence": 0.9}],
            "conflicts": [], "uncertain": [], "extractConfidence": 0.9,
        },
    }


def _write_input(tmp_path, records):
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    with (input_dir / "records.jsonl").open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return input_dir


def _full_payload(conf=0.9):
    cell = lambda v, c=conf: {"value": v, "confidence": c}  # noqa: E731
    return {
        "structured": {
            "数据来源类型": cell("官方媒体"), "可能的发布时间": cell("2021-06"),
            "涉及人物、地点或组织": cell(["张伟", "某市"]), "时空变迁信息": cell("签约仪式于 6 月 12 日举行"),
        },
        "basic": {
            "知识层次": cell("大众常识"), "涉及的知识点列表": cell(["重点项目签约", "总投资", "市政建设"]),
            "主要一级行业": cell("公共管理"), "行业场景": cell("政务活动"),
            "行业类型": cell("政府"), "涉及的角色列表": cell(["市委常委"]),
        },
        "related": {
            "文章风格": cell("客观报道"), "内容类别": cell("消息"), "价值观": cell("中性"),
            "历史关联": cell("无"), "国家关联": cell("中国"), "宗教关联": cell("无"),
        },
        "uncertain": [],
    }


def test_dataset_row_format(tmp_path, monkeypatch):
    """数据集行与交付说明 §五样例一致：16 字段取值、两个置信度、复核状态默认。"""
    monkeypatch.setattr(op.llm_client, "chat", lambda *a, **k: json.dumps(_full_payload(), ensure_ascii=False))
    result = run(_write_input(tmp_path, [_record("d1")]), tmp_path / "out", validate_params({}), _noop_log)
    assert result["summary"] == {"total": 1, "filled": 1, "review": 0, "failed": 0}
    row = json.loads((tmp_path / "out" / "records.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert set(row["structured"]) == set(config.STRUCTURED_FIELDS)
    assert set(row["basic"]) == set(config.BASIC_FIELDS)
    assert set(row["related"]) == set(config.RELATED_FIELDS)
    assert row["structured"]["涉及人物、地点或组织"] == ["张伟", "某市"]
    assert row["fillConfidence"] == 0.9 and row["extractConfidence"] == 0.9
    assert row["reviewStatus"] == "未进入复核" and row["revisionStatus"] == "—"
    detail = json.loads((tmp_path / "out" / "fields_detail.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert detail["fieldConfidences"]["basic"]["知识层次"] == 0.9


def test_missing_and_enum_problems(tmp_path, monkeypatch):
    """缺字段兜底"无"、非法枚举纠正、低置信 → 复核且继续下游。"""
    payload = _full_payload(conf=0.9)
    del payload["basic"]["行业场景"]
    payload["related"]["价值观"] = {"value": "积极", "confidence": 0.9}
    payload["related"]["历史关联"] = {"value": "无", "confidence": 0.5}
    payload["basic"]["涉及的知识点列表"] = {"value": "单值字符串", "confidence": 0.9}
    monkeypatch.setattr(op.llm_client, "chat", lambda *a, **k: json.dumps(payload, ensure_ascii=False))
    result = run(_write_input(tmp_path, [_record("d2")]), tmp_path / "out", validate_params({}), _noop_log)
    assert result["summary"] == {"total": 1, "filled": 1, "review": 1, "failed": 0}
    row = json.loads((tmp_path / "out" / "records.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert row["basic"]["行业场景"] == "无"
    assert row["related"]["价值观"] == "中性"
    assert row["basic"]["涉及的知识点列表"] == ["单值字符串"]
    assert row["fillConfidence"] == 0.5 and row["reviewStatus"] == "待复核"
    reason = result["review"][0]["reviewReason"]
    assert "行业场景 缺失" in reason and "价值观非法值" in reason and "低于阈值" in reason


def test_model_failure_goes_failed(tmp_path, monkeypatch):
    from meta_field_fill.utils.llm_client import LlmError
    def _boom(messages, **kwargs):
        raise LlmError("HTTP 500")
    monkeypatch.setattr(op.llm_client, "chat", _boom)
    result = run(_write_input(tmp_path, [_record("d3")]), tmp_path / "out", validate_params({}), _noop_log)
    assert result["summary"] == {"total": 1, "filled": 0, "review": 1, "failed": 1}
    assert not (tmp_path / "out" / "records.jsonl").read_text(encoding="utf-8").strip()


def test_missing_input_file(tmp_path):
    with pytest.raises(ValueError, match="records.jsonl"):
        run(tmp_path, tmp_path / "out", validate_params({}), _noop_log)
