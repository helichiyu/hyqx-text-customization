"""fml_formula_recognize 离线测试：语法校验 / 修复链 / 截断 / 分流（模型调用 monkeypatch）。"""

import json
import sys
from pathlib import Path

import pytest
from PIL import Image

PKG_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PKG_ROOT))

from fml_formula_recognize import operator as op  # noqa: E402
from fml_formula_recognize.operator import check_latex, run, strip_delimiters, validate_params  # noqa: E402
from fml_formula_recognize.utils.llm_client import LlmError  # noqa: E402


def _noop_log(*args, **kwargs):
    pass


def _make_input(tmp_path, instances):
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    for inst in instances:
        crop = input_dir / inst["crop"]
        crop.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (200, 60), "white").save(crop)
    rec = {"docId": "doc1", "fileName": "doc1.pdf", "pageCount": 1,
           "checksum": "x" * 64, "instances": instances, "instanceCount": len(instances)}
    with (input_dir / "records.jsonl").open("w", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return input_dir


def _inst(iid, crop=None):
    return {"instanceId": iid, "pageNo": 1, "bbox": [100, 100, 500, 160],
            "bboxPixel": [60, 60, 300, 96], "hasNumber": True, "locateConfidence": 0.95,
            "crop": crop or f"crops/doc1/{iid}.png",
            "chapterTitle": "第二章 极限", "contextText": "其中 a 为分子，b 为分母。"}


def _payload(latex=r"\frac{a}{b}", rc=0.93, sc=0.85, symbols=None, definition="第 2 段"):
    return {
        "latex": latex,
        "symbols": symbols if symbols is not None else [
            {"symbol": "a", "meaning": "分子", "unit": None},
            {"symbol": "b", "meaning": "分母", "unit": None}],
        "context": {"chapter": "第二章 极限", "number": "(2-3)", "definition": definition},
        "recognitionConfidence": rc, "semanticConfidence": sc, "uncertain": [],
    }


def test_latex_checker():
    assert check_latex(r"\frac{a}{b} + \sqrt{x}") is None
    assert check_latex(r"\begin{aligned} a &= b \\ c &= d \end{aligned}") is None
    assert check_latex("") == "LaTeX 为空"
    assert "花括号" in check_latex(r"\frac{a}{b")
    assert "环境" in check_latex(r"\begin{cases} a \end{matrix}")
    assert "环境未闭合" in check_latex(r"\begin{matrix} a")
    assert "left" in check_latex(r"\left( a + b")
    assert strip_delimiters(r"$$\frac{a}{b}$$") == r"\frac{a}{b}"
    assert strip_delimiters(r"\[ E = mc^2 \]") == r"E = mc^2"


def test_clean_row(tmp_path, monkeypatch):
    monkeypatch.setattr(op.llm_client, "chat_vision",
                        lambda *a, **k: json.dumps(_payload(), ensure_ascii=False))
    result = run(_make_input(tmp_path, [_inst("i1")]), tmp_path / "out", validate_params({}), _noop_log)
    assert result["summary"] == {"docs": 1, "instances": 1, "recognized": 1, "review": 0, "failed": 0}
    row = json.loads((tmp_path / "out" / "records.jsonl").read_text(encoding="utf-8").splitlines()[0])
    # 数据集行与 §五样例一致；回溯字段不进数据集
    assert set(row) == {"instanceId", "latex", "symbols", "context",
                        "recognitionConfidence", "semanticConfidence", "reviewStatus", "revisionStatus"}
    assert row["reviewStatus"] == "未进入复核"
    trace = json.loads((tmp_path / "out" / "trace.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert trace["bbox"] == [100, 100, 500, 160] and trace["pageNo"] == 1


def test_repair_chain(tmp_path, monkeypatch):
    """非法 LaTeX → 修复 Prompt → 再校验通过，复核记录标注经修复。"""
    monkeypatch.setattr(op.llm_client, "chat_vision",
                        lambda *a, **k: json.dumps(_payload(latex=r"\frac{a}{b"), ensure_ascii=False))
    repair_calls = {"n": 0}

    def _repair(messages, **kwargs):
        repair_calls["n"] += 1
        assert kwargs.get("json_mode") is False
        return r"\frac{a}{b}"

    monkeypatch.setattr(op.llm_client, "chat", _repair)
    result = run(_make_input(tmp_path, [_inst("i1")]), tmp_path / "out", validate_params({}), _noop_log)
    assert repair_calls["n"] == 1
    row = json.loads((tmp_path / "out" / "records.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert row["latex"] == r"\frac{a}{b}"
    assert "经修复" in result["review"][0]["reviewReason"]


def test_repair_failure_and_low_confidence(tmp_path, monkeypatch):
    """修复仍失败 + 低置信 → 复核；符号缺失 → 复核。"""
    payload = _payload(latex=r"\frac{a}{b", rc=0.5, symbols="not-a-list")
    monkeypatch.setattr(op.llm_client, "chat_vision",
                        lambda *a, **k: json.dumps(payload, ensure_ascii=False))
    monkeypatch.setattr(op.llm_client, "chat", lambda *a, **k: "")  # 修复输出空
    result = run(_make_input(tmp_path, [_inst("i1")]), tmp_path / "out", validate_params({}), _noop_log)
    reason = result["review"][0]["reviewReason"]
    assert "语法非法" in reason and "识别置信度低于阈值" in reason and "符号缺失" in reason
    row = json.loads((tmp_path / "out" / "records.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert row["reviewStatus"] == "待复核" and row["symbols"] == []


def test_model_failure_goes_failed(tmp_path, monkeypatch):
    def _boom(*a, **k):
        raise LlmError("HTTP 500")
    monkeypatch.setattr(op.llm_client, "chat_vision", _boom)
    result = run(_make_input(tmp_path, [_inst("i1")]), tmp_path / "out", validate_params({}), _noop_log)
    assert result["summary"]["recognized"] == 0 and result["summary"]["failed"] == 1
    assert not (tmp_path / "out" / "records.jsonl").read_text(encoding="utf-8").strip()


def test_confidence_clamped(tmp_path, monkeypatch):
    monkeypatch.setattr(op.llm_client, "chat_vision",
                        lambda *a, **k: json.dumps(_payload(rc=1.5, sc=0.9), ensure_ascii=False))
    result = run(_make_input(tmp_path, [_inst("i1")]), tmp_path / "out", validate_params({}), _noop_log)
    row = json.loads((tmp_path / "out" / "records.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert row["recognitionConfidence"] == 0.98


def test_missing_input_file(tmp_path):
    with pytest.raises(ValueError, match="records.jsonl"):
        run(tmp_path, tmp_path / "out", validate_params({}), _noop_log)
