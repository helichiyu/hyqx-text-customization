"""公式识别与结构化标注 · 算子核心（公式文本 环节②③，一次调用五字段 + 语法校验修复链）。

输入：fml_formula_locate 的 records.jsonl（含 instances）。
流程：公式裁切图 + 页上下文 → 一次调用出 latex/symbols/context/双置信度（§4.1 一次调用）
→ §4.6 校验（JSON/latex 非空 → 重试；定界符剥除；置信度截断）
→ LaTeX 语法规则校验，非法 → 修复 Prompt（纯文本）→ 再校验 → 仍失败进复核
→ 符号缺失/定义无法定位/置信度缺失或低置信 → 进复核（保留数据集行）。
数据集一行一个公式；页码/bbox/上下文范围只进 trace.jsonl（回溯用，不进数据集）。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .configs import config, prompts
from .utils import llm_client, review_codes
from .utils.llm_client import JsonParseError, LlmError

OPERATOR_NAME = "公式识别与结构化标注"
ALLOWED_SUFFIXES = (".jsonl", ".zip")

PARAM_DEFAULTS: dict[str, Any] = {
    "confidence_threshold": config.CONFIDENCE_THRESHOLD,
    "concurrency": 4,
}

RECORDS_FILE = "records.jsonl"
REVIEW_FILE = "review.jsonl"
TRACE_FILE = "trace.jsonl"

_DELIMITER_RE = re.compile(r"\\\(|\\\)|\\\[|\\\]|\$\$?")


def validate_params(params: dict[str, Any]) -> dict[str, Any]:
    merged = {**PARAM_DEFAULTS, **(params or {})}
    if not (0.0 < float(merged["confidence_threshold"]) < 1.0):
        raise ValueError("confidence_threshold 须在 (0, 1) 之间")
    return merged


# ---------- LaTeX 语法规则校验（规则解析器，交付说明 §三 环节②#3） ----------

def strip_delimiters(latex: str) -> str:
    """剥除 $、$$、\\[ \\]、\\( \\) 定界符。"""

    return _DELIMITER_RE.sub("", latex).strip()


def check_latex(latex: str) -> str | None:
    """规则校验：返回错误信息，合法返回 None。"""

    if not latex or not latex.strip():
        return "LaTeX 为空"
    if latex.count("{") != latex.count("}"):
        return "花括号不配对"
    depth = 0
    for ch in latex:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        if depth < 0:
            return "花括号闭合先于开启"
    stack: list[str] = []
    for m in re.finditer(r"\\(begin|end)\{([^}]*)\}", latex):
        kind, env = m.group(1), m.group(2)
        if kind == "begin":
            stack.append(env)
        else:
            if not stack or stack[-1] != env:
                return f"环境不配对：\\end{{{env}}}"
            stack.pop()
    if stack:
        return f"环境未闭合：\\begin{{{stack[-1]}}}"
    left = latex.count("\\left")
    right = latex.count("\\right")
    if left != right:
        return f"\\left/\\right 不配对（{left}/{right}）"
    if "$" in latex:
        return "仍含 $ 定界符"
    return None


# ---------- 模型调用 ----------

def _recognize(instance: dict[str, Any], input_root: Path) -> dict[str, Any]:
    """一次调用出五字段；JSON 解析失败 / latex 空 → 重试 1 次。"""

    user = prompts.RECOGNIZE_USER_TEMPLATE.format(
        pageNo=instance["pageNo"], bbox=instance["bbox"],
        chapterTitle=instance.get("chapterTitle") or "（无）",
        contextText=instance.get("contextText") or "（无）")
    last_err: str | None = None
    for _ in range(2):
        try:
            obj = llm_client.extract_json(llm_client.chat_vision(
                prompts.RECOGNIZE_SYSTEM_PROMPT, user, input_root / instance["crop"],
                max_tokens=4096, max_long_edge=config.IMAGE_MAX_LONG_EDGE))
            if not str(obj.get("latex") or "").strip():
                raise JsonParseError("latex 为空")
            return obj
        except (JsonParseError, LlmError) as e:
            last_err = str(e)
    raise LlmError(f"公式识别失败：{last_err}")


def _repair_latex(latex: str, error: str) -> str | None:
    """修复 Prompt（纯文本模式）；无法修复返回 None。"""

    try:
        out = llm_client.chat(
            [{"role": "user", "content": prompts.REPAIR_TEMPLATE.format(latex=latex, error=error)}],
            json_mode=False, max_tokens=2048)
    except LlmError:
        return None
    fixed = strip_delimiters(out.splitlines()[0] if out else "")
    return fixed or None


def _null_if_placeholder(value: Any) -> Any:
    """模型偶发把 null 写成字符串 "null"/"None"/"无"，归一为 None。"""

    if isinstance(value, str) and value.strip().lower() in ("null", "none", ""):
        return None
    return value


def _process_instance(doc: dict[str, Any], instance: dict[str, Any],
                      input_root: Path, threshold: float) -> dict[str, Any]:
    iid = instance["instanceId"]
    try:
        obj = _recognize(instance, input_root)
    except LlmError as e:
        return {"failed": {"name": iid, "reason": str(e), "code": "model_call_failed"},
                "review": {"instanceId": iid, "docId": doc["docId"], "latex": None,
                           "code": "model_call_failed", "reviewReason": str(e)}}

    latex = strip_delimiters(str(obj.get("latex") or ""))
    reasons: list[str] = []
    repaired = False
    latex_invalid = False

    # LaTeX 语法校验 → 修复链
    error = check_latex(latex)
    if error:
        fixed = _repair_latex(latex, error)
        if fixed and not check_latex(fixed):
            latex = fixed
            repaired = True
            reasons.append("LaTeX 经修复 Prompt 修正")
        else:
            latex_invalid = True
            reasons.append(f"LaTeX 语法非法（{error}；修复后仍失败）")

    # 符号校验
    symbols = obj.get("symbols")
    symbols_invalid = (not isinstance(symbols, list)
                       or any(not isinstance(s, dict) or not s.get("symbol") for s in symbols))
    if symbols_invalid:
        reasons.append("符号缺失或格式非法")
        symbols = symbols if isinstance(symbols, list) else []
    symbols = [{"symbol": str(s.get("symbol")), "meaning": _null_if_placeholder(s.get("meaning")),
                "unit": _null_if_placeholder(s.get("unit"))}
               for s in symbols if isinstance(s, dict) and s.get("symbol")]

    context = obj.get("context") or {}
    context = {"chapter": _null_if_placeholder(context.get("chapter")),
               "number": _null_if_placeholder(context.get("number")),
               "definition": _null_if_placeholder(context.get("definition"))}

    rec_conf = llm_client.clamp_confidence(obj.get("recognitionConfidence"))
    sem_conf = llm_client.clamp_confidence(obj.get("semanticConfidence"))
    confidence_missing = rec_conf is None or sem_conf is None
    low_rec = rec_conf is not None and rec_conf < threshold
    low_sem = sem_conf is not None and sem_conf < threshold
    if confidence_missing:
        reasons.append("置信度缺失")
    else:
        if low_rec:
            reasons.append("识别置信度低于阈值")
        if low_sem:
            reasons.append("语义标注置信度低于阈值")
    definition_missing = bool(symbols) and not context.get("definition")
    if definition_missing:
        reasons.append("变量定义位置无法定位")

    row = {
        "instanceId": iid,
        "latex": latex,
        "symbols": symbols,
        "context": context,
        "recognitionConfidence": rec_conf,
        "semanticConfidence": sem_conf,
        "reviewStatus": "待复核" if reasons else "未进入复核",
        "revisionStatus": "未修正" if reasons else "—",
    }
    trace = {"instanceId": iid, "docId": doc["docId"], "fileName": doc.get("fileName"),
             "pageNo": instance["pageNo"], "bbox": instance["bbox"], "crop": instance["crop"],
             "chapterTitle": instance.get("chapterTitle"),
             "uncertain": obj.get("uncertain") or []}
    result: dict[str, Any] = {"row": row, "trace": trace}
    if reasons:
        code = review_codes.pick(
            (latex_invalid, "latex_invalid"),
            (repaired, "latex_repaired"),
            (symbols_invalid, "symbols_invalid"),
            (definition_missing, "definition_missing"),
            (confidence_missing, "confidence_missing"),
            (low_rec, "low_recognition_confidence"),
            (low_sem, "low_semantic_confidence"))
        result["review"] = {**row, "docId": doc["docId"], "code": code,
                            "reviewReason": "；".join(reasons)}
    return result


def run(input_dir: Path, output_dir: Path, params: dict[str, Any], log) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    src = input_dir / RECORDS_FILE
    if not src.exists():
        raise ValueError(f"输入目录缺少 {RECORDS_FILE}（上游 fml_formula_locate 产物）")
    docs = [json.loads(line) for line in src.read_text(encoding="utf-8").splitlines() if line.strip()]
    threshold = float(params["confidence_threshold"])

    tasks = [(doc, inst) for doc in docs for inst in doc.get("instances", [])]
    rows: list[dict[str, Any]] = []
    traces: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    failed: list[dict[str, str]] = []
    lineage: list[dict[str, Any]] = []

    log("进入公式识别 %d 个实例（%d 份文档）", len(tasks), len(docs))
    results = llm_client.run_concurrent(
        tasks, lambda t: _process_instance(t[0], t[1], input_dir, threshold),
        concurrency=int(params["concurrency"]))

    for (doc, inst), outcome in zip(tasks, results):
        iid = inst["instanceId"]
        base = {"sample_id": iid, "source_file": doc.get("fileName")}
        if "failed" in outcome:
            failed.append(outcome["failed"])
            review.append(outcome["review"])
            lineage.append({**base, "action": "fail", "reason": outcome["failed"]["reason"]})
            continue
        rows.append(outcome["row"])
        traces.append(outcome["trace"])
        if "review" in outcome:
            review.append(outcome["review"])
            lineage.append({**base, "action": "review", "reason": outcome["review"]["reviewReason"]})
        else:
            lineage.append({**base, "action": "keep",
                            "metrics": {"recognition_confidence": outcome["row"]["recognitionConfidence"],
                                        "semantic_confidence": outcome["row"]["semanticConfidence"]}})

    for name, items in ((RECORDS_FILE, rows), (REVIEW_FILE, review), (TRACE_FILE, traces)):
        with (output_dir / name).open("w", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

    log("识别完成：数据集 %d 行（%d 条待复核），%d 条失败", len(rows), len(review) - len(failed), len(failed))
    return {
        "records_file": RECORDS_FILE,
        "summary": {
            "docs": len(docs), "instances": len(tasks), "recognized": len(rows),
            "review": len(review), "failed": len(failed),
        },
        "skipped": [],
        "failed": failed,
        "review": review,
        "sample_lineage": lineage,
    }
