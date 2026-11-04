"""meta_fact_extract 离线测试：合并去重 / 冲突标记 / 失败分流（模型调用 monkeypatch）。"""

import json
import sys
from pathlib import Path

import pytest

PKG_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PKG_ROOT))

from meta_fact_extract import operator as op  # noqa: E402
from meta_fact_extract.operator import run, validate_params  # noqa: E402


def _noop_log(*args, **kwargs):
    pass


def _record(doc_id, title, slices_text):
    return {
        "docId": doc_id, "fileName": f"{doc_id}.html", "title": title,
        "textLength": sum(len(t) for t in slices_text), "sliceCount": len(slices_text),
        "slices": [
            {"sliceId": f"{doc_id}-s{i:02d}", "index": i, "text": t, "charCount": len(t)}
            for i, t in enumerate(slices_text, start=1)
        ],
    }


def _write_input(tmp_path, records):
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    with (input_dir / "records.jsonl").open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return input_dir


def _fake_chat_factory(mapping, default=None):
    def _fake(messages, **kwargs):
        user = messages[-1]["content"]
        for key, payload in mapping.items():
            if key in user:
                if isinstance(payload, Exception):
                    raise payload
                return payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
        if default is not None:
            return json.dumps(default, ensure_ascii=False)
        raise AssertionError(f"未登记的模型输入：{user[:50]}")
    return _fake


EMPTY_RESULT = {"source_type": {}, "time_candidates": [], "entities": [], "conflicts": [], "uncertain": []}


def test_merge_dedupe_and_conflict(tmp_path, monkeypatch):
    """两片各报一个时间候选 + 重复实体 → 去重、时间冲突标记、继续下游并进复核。"""
    mapping = {
        "第一段": {
            "source_type": {"value": "官方媒体", "evidence": "据某市日报", "confidence": 0.9},
            "time_candidates": [{"value": "2021 年 6 月", "granularity": "月", "evidence": "...", "position": "第 1 段", "confidence": 0.9}],
            "entities": [{"mention": "张伟", "kind": "person", "evidence": "...", "position": "第 1 段", "confidence": 0.9}],
            "conflicts": [], "uncertain": [],
        },
        "第二段": {
            "source_type": {"value": "官方媒体", "evidence": "据某市日报", "confidence": 0.85},
            "time_candidates": [{"value": "2022 年 6 月", "granularity": "月", "evidence": "...", "position": "第 3 段", "confidence": 0.8}],
            "entities": [
                {"mention": "张伟", "kind": "person", "evidence": "...", "position": "第 3 段", "confidence": 0.7},
                {"mention": "某市", "kind": "place", "evidence": "...", "position": "第 3 段", "confidence": 0.95},
            ],
            "conflicts": [], "uncertain": [],
        },
    }
    monkeypatch.setattr(op.llm_client, "chat", _fake_chat_factory(mapping))
    rec = _record("d1", "标题", ["第一段……", "第二段……"])
    result = run(_write_input(tmp_path, [rec]), tmp_path / "out", validate_params({}), _noop_log)

    assert result["summary"] == {"total": 1, "extracted": 1, "review": 1, "failed": 0}
    facts = json.loads((tmp_path / "out" / "records.jsonl").read_text(encoding="utf-8").splitlines()[0])["facts"]
    assert sorted(t["value"] for t in facts["timeCandidates"]) == ["2021 年 6 月", "2022 年 6 月"]
    assert [e["mention"] for e in facts["entities"]] == ["张伟", "某市"]  # 张伟去重，留 0.9 那条
    assert facts["entities"][0]["confidence"] == 0.9
    assert any(c["field"] == "time" for c in facts["conflicts"])
    assert facts["extractConfidence"] == 0.8  # 来源/时间/实体最低分（张伟低分副本已被去重）
    review = json.loads((tmp_path / "out" / "review.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert "冲突" in review["reviewReason"]
    assert review["code"] == "candidate_conflict"


def test_all_slices_fail_goes_failed_only(tmp_path, monkeypatch):
    """全部切片调用失败 → 不进下游，只进复核/失败清单。"""
    monkeypatch.setattr(op.llm_client, "chat", _fake_chat_factory({}, default=None))
    def _boom(messages, **kwargs):
        from meta_fact_extract.utils.llm_client import LlmError
        raise LlmError("HTTP 500")
    monkeypatch.setattr(op.llm_client, "chat", _boom)
    rec = _record("d2", "标题", ["正文"])
    result = run(_write_input(tmp_path, [rec]), tmp_path / "out", validate_params({}), _noop_log)
    assert result["summary"] == {"total": 1, "extracted": 0, "review": 1, "failed": 1}
    assert not (tmp_path / "out" / "records.jsonl").read_text(encoding="utf-8").strip()
    assert "全部切片" in result["failed"][0]["reason"]
    assert result["failed"][0]["code"] == "model_call_failed"
    assert result["review"][0]["code"] == "model_call_failed"


def test_missing_source_type_reviews_but_continues(tmp_path, monkeypatch):
    """来源类型缺失 → 进复核且继续下游（交付说明：缺失进复核，未要求阻断）。"""
    mapping = {
        "正文": {
            "source_type": {"value": None, "evidence": None, "confidence": None},
            "time_candidates": [{"value": "6 月 12 日", "granularity": "日", "evidence": "...", "position": "第 1 段", "confidence": 0.95}],
            "entities": [{"mention": "某市", "kind": "place", "evidence": "...", "position": "第 1 段", "confidence": 0.9}],
            "conflicts": [], "uncertain": [],
        },
    }
    monkeypatch.setattr(op.llm_client, "chat", _fake_chat_factory(mapping))
    rec = _record("d3", "标题", ["正文"])
    result = run(_write_input(tmp_path, [rec]), tmp_path / "out", validate_params({}), _noop_log)
    assert result["summary"] == {"total": 1, "extracted": 1, "review": 1, "failed": 0}
    assert "来源类型缺失" in result["review"][0]["reviewReason"]
    assert result["review"][0]["code"] == "source_type_missing"


def test_confidence_clamped(tmp_path, monkeypatch):
    """置信度越界截断到 0.98。"""
    mapping = {
        "正文": {
            "source_type": {"value": "自媒体", "evidence": "...", "confidence": 1.5},
            "time_candidates": [], "entities": [], "conflicts": [], "uncertain": [],
        },
    }
    monkeypatch.setattr(op.llm_client, "chat", _fake_chat_factory(mapping))
    rec = _record("d4", "标题", ["正文"])
    result = run(_write_input(tmp_path, [rec]), tmp_path / "out", validate_params({}), _noop_log)
    facts = json.loads((tmp_path / "out" / "records.jsonl").read_text(encoding="utf-8").splitlines()[0])["facts"]
    assert facts["sourceType"]["confidence"] == 0.98


def test_parse_failure_retries_then_slice_failed(tmp_path, monkeypatch):
    """单片两次返回非 JSON → 该片失败，其余片继续，uncertain 记录。"""
    calls = {"n": 0}
    def _mixed(messages, **kwargs):
        user = messages[-1]["content"]
        if "好片" in user:
            return json.dumps({
                "source_type": {"value": "转载", "evidence": "...", "confidence": 0.9},
                "time_candidates": [], "entities": [], "conflicts": [], "uncertain": [],
            }, ensure_ascii=False)
        calls["n"] += 1
        return "这不是JSON"
    monkeypatch.setattr(op.llm_client, "chat", _mixed)
    rec = _record("d5", "标题", ["坏片", "好片"])
    result = run(_write_input(tmp_path, [rec]), tmp_path / "out", validate_params({}), _noop_log)
    assert calls["n"] == 2  # 解析失败重试 1 次
    assert result["summary"]["extracted"] == 1
    facts = json.loads((tmp_path / "out" / "records.jsonl").read_text(encoding="utf-8").splitlines()[0])["facts"]
    assert any("切片抽取失败" in u for u in facts["uncertain"])


def test_missing_input_file(tmp_path):
    with pytest.raises(ValueError, match="records.jsonl"):
        run(tmp_path, tmp_path / "out", validate_params({}), _noop_log)
