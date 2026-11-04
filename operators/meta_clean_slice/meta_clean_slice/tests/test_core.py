"""meta_clean_slice 核心离线测试（不调模型）。"""

import json
import sys
from pathlib import Path

import pytest

PKG_ROOT = Path(__file__).resolve().parents[2]
SAMPLES = Path(__file__).resolve().parents[4] / "samples_pool" / "meta"
sys.path.insert(0, str(PKG_ROOT))

from meta_clean_slice.operator import run, validate_params  # noqa: E402
from meta_clean_slice.utils.html_text import extract  # noqa: E402


def _noop_log(*args, **kwargs):
    pass


def test_extract_news():
    doc = extract((SAMPLES / "news_001.html").read_bytes())
    assert doc.title == "某市地铁3号线正式通车运营"
    assert any("地铁3号线" in p for p in doc.paragraphs)
    assert doc.link_ratio < 0.1


def test_extract_gbk():
    html = "<html><body><p>这是一段 GB18030 编码的中文正文段落，长度足够通过校验。</p></body></html>"
    doc = extract(html.encode("gb18030"))
    assert any("GB18030" in p for p in doc.paragraphs)


def test_run_on_sample_pool(tmp_path):
    result = run(SAMPLES, tmp_path, validate_params({}), _noop_log)
    assert result["summary"] == {"total": 5, "kept": 4, "skipped": 1}
    assert result["skipped"][0]["name"] == "nonnews_navlist.html"
    assert result["skipped"][0]["reason"] == "导航页"

    records = [json.loads(line) for line in (tmp_path / "records.jsonl").read_text(encoding="utf-8").splitlines()]
    by_id = {r["docId"]: r for r in records}
    assert set(by_id) == {"news_001", "news_002", "nonnews_product", "nonnews_tutorial"}
    for rec in records:
        assert rec["sliceCount"] == len(rec["slices"]) >= 1
        for s in rec["slices"]:
            assert s["charCount"] <= 2000

    skip_rows = [r for r in result["sample_lineage"] if r["action"] == "skip"]
    assert len(skip_rows) == 1


def test_blank_and_short(tmp_path):
    (tmp_path / "blank.html").write_text("<html><body></body></html>", encoding="utf-8")
    (tmp_path / "short.html").write_text("<html><body><p>太短</p></body></html>", encoding="utf-8")
    result = run(tmp_path, tmp_path / "out", validate_params({}), _noop_log)
    reasons = {s["name"]: s["reason"] for s in result["skipped"]}
    assert reasons["blank.html"] == "空白页"
    assert reasons["short.html"] == "无有效段落"


def test_slicing_overlap_and_hard_split(tmp_path):
    para = "字" * 4500  # 超长段落硬切
    (tmp_path / "long.html").write_text(f"<html><body><p>{para}</p></body></html>", encoding="utf-8")
    result = run(tmp_path, tmp_path / "out", validate_params({}), _noop_log)
    rec = json.loads((tmp_path / "out" / "records.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert rec["sliceCount"] == 3  # 4500 / (2000-200) → 3 片
    lens = [s["charCount"] for s in rec["slices"]]
    assert lens[0] == 2000 and lens[-1] < 2000
    # 重叠：第二片开头 = 第一片末尾 200 字
    assert rec["slices"][1]["text"][:200] == rec["slices"][0]["text"][-200:]


def test_params_validation():
    with pytest.raises(ValueError):
        validate_params({"slice_max_chars": 10})
    with pytest.raises(ValueError):
        validate_params({"slice_max_chars": 2000, "slice_overlap_chars": 2000})
