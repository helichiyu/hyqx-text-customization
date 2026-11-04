"""meta_genre_judge 离线测试：规则粗筛与模型路径（模型调用 monkeypatch）。"""

import json
import sys
from pathlib import Path

import pytest

PKG_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PKG_ROOT))

from meta_genre_judge import operator as op  # noqa: E402
from meta_genre_judge.operator import run, validate_params  # noqa: E402


def _noop_log(*args, **kwargs):
    pass


def _record(doc_id, title, text, source=None):
    return {
        "docId": doc_id, "fileName": f"{doc_id}.html", "title": title, "source": source,
        "textLength": len(text), "sliceCount": 1,
        "slices": [{"sliceId": f"{doc_id}-s01", "index": 1, "text": text, "charCount": len(text)}],
    }


def _write_input(tmp_path, records):
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    with (input_dir / "records.jsonl").open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return input_dir


def test_rule_screen_skips_without_model(tmp_path, monkeypatch):
    def _no_call(*args, **kwargs):
        raise AssertionError("规则粗筛命中的文档不应调模型")

    monkeypatch.setattr(op.llm_client, "chat", _no_call)
    records = [
        _record("ad", "XX牌空气炸锅 限时特惠", "原价599元，点击立即购买！好评率99%。"),
        _record("tut", "Python入门教程：列表推导式", "本文介绍列表推导式的用法，" * 10),
    ]
    result = run(_write_input(tmp_path, records), tmp_path / "out", validate_params({}), _noop_log)
    assert result["summary"] == {"total": 2, "news": 0, "review": 0, "skipped": 2}
    reasons = {s["name"]: s["reason"] for s in result["skipped"]}
    assert reasons["ad"] == "规则粗筛-广告/产品页"
    assert reasons["tut"] == "规则粗筛-教程类"


def _fake_chat_factory(mapping):
    def _fake(messages, **kwargs):
        user = messages[-1]["content"]
        for key, payload in mapping.items():
            if key in user:
                return json.dumps(payload, ensure_ascii=False)
        raise AssertionError(f"未登记的模型输入：{user[:50]}")
    return _fake


def test_model_paths(tmp_path, monkeypatch):
    mapping = {
        "地铁通车": {"is_news": True, "category": "消息", "conditions": {"event": True, "timeliness": True, "factual": True, "public": True}, "confidence": 0.95, "reason": "ok", "evidence": []},
        "社区随笔": {"is_news": False, "category": "评论", "conditions": {"event": False, "timeliness": False, "factual": False, "public": True}, "confidence": 0.9, "reason": "观点为主", "evidence": []},
        "传闻": {"is_news": True, "category": "其他", "conditions": {"event": True, "timeliness": False, "factual": True, "public": True}, "confidence": 0.6, "reason": "时效不明", "evidence": []},
    }
    monkeypatch.setattr(op.llm_client, "chat", _fake_chat_factory(mapping))
    records = [
        _record("n1", "某市地铁通车", "6月12日，某市地铁3号线通车。" * 5, "某市日报"),
        _record("n2", "社区随笔", "我认为城市发展应该更慢一点。" * 10),
        _record("n3", "传闻某事", "据传某地发生某事，时间不详。" * 10),
    ]
    result = run(_write_input(tmp_path, records), tmp_path / "out", validate_params({}), _noop_log)
    assert result["summary"] == {"total": 3, "news": 1, "review": 1, "skipped": 1}

    kept = [json.loads(l) for l in (tmp_path / "out" / "records.jsonl").read_text(encoding="utf-8").splitlines()]
    assert kept[0]["docId"] == "n1" and kept[0]["genre"]["category"] == "消息"

    review = [json.loads(l) for l in (tmp_path / "out" / "review.jsonl").read_text(encoding="utf-8").splitlines()]
    assert review[0]["docId"] == "n3" and "置信度" in review[0]["reviewReason"]

    actions = {r["sample_id"]: r["action"] for r in result["sample_lineage"]}
    assert actions == {"n1": "keep", "n2": "skip", "n3": "review"}


def test_parse_failure_goes_review(tmp_path, monkeypatch):
    monkeypatch.setattr(op.llm_client, "chat", lambda *a, **k: "这不是JSON")
    records = [_record("bad", "普通标题", "一段没有任何触发词的正文内容。" * 10)]
    result = run(_write_input(tmp_path, records), tmp_path / "out", validate_params({}), _noop_log)
    assert result["summary"]["review"] == 1
    assert "解析失败" in result["review"][0]["reviewReason"]


def test_missing_input_file(tmp_path):
    with pytest.raises(ValueError, match="records.jsonl"):
        run(tmp_path, tmp_path / "out", validate_params({}), _noop_log)
