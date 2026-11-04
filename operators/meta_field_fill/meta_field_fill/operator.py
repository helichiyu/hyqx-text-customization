"""元信息三组补全 · 算子核心（文本元信息 环节③，文档级一次调用，产线末位含汇总）。

输入：meta_fact_extract 的 records.jsonl（含 facts）。
流程：标题 + 正文（拼接截断）+ 事实清单 → 一次调用出 16 字段（4+6+6）逐字段置信度
→ 字段校验（缺失/枚举非法 → 进复核并兜底"无"）→ 数据集行（对齐交付说明 §五样例）。
分流：模型输出失败 → 仅复核不进下游；低置信/字段异常 → 复核 + 继续下游。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .configs import config, prompts
from .utils import llm_client, review_codes
from .utils.llm_client import JsonParseError, LlmError

OPERATOR_NAME = "元信息三组补全"
ALLOWED_SUFFIXES = (".jsonl", ".zip")

PARAM_DEFAULTS: dict[str, Any] = {
    "confidence_threshold": config.FILL_CONFIDENCE_THRESHOLD,
    "max_text_chars": config.MAX_TEXT_CHARS,
    "concurrency": 4,
}

RECORDS_FILE = "records.jsonl"
REVIEW_FILE = "review.jsonl"
DETAIL_FILE = "fields_detail.jsonl"


def validate_params(params: dict[str, Any]) -> dict[str, Any]:
    merged = {**PARAM_DEFAULTS, **(params or {})}
    if not (0.0 < float(merged["confidence_threshold"]) < 1.0):
        raise ValueError("confidence_threshold 须在 (0, 1) 之间")
    if int(merged["max_text_chars"]) < 500:
        raise ValueError("max_text_chars 须 ≥500")
    return merged


def _doc_text(rec: dict[str, Any], max_chars: int) -> str:
    return "".join(s["text"] for s in rec.get("slices", []))[:max_chars]


def _facts_json(rec: dict[str, Any]) -> str:
    facts = rec.get("facts") or {}
    brief = {
        "sourceType": facts.get("sourceType"),
        "timeCandidates": facts.get("timeCandidates"),
        "entities": facts.get("entities"),
        "conflicts": facts.get("conflicts"),
    }
    return json.dumps(brief, ensure_ascii=False)


def _fill_one(rec: dict[str, Any], max_chars: int) -> dict[str, Any]:
    """文档级一次补全；JSON 解析失败重试 1 次（传输重试由 llm_client 承担）。"""

    system = prompts.FILL_SYSTEM_PROMPT.replace("{facts_json}", _facts_json(rec))
    user = prompts.FILL_USER_TEMPLATE.format(
        title=rec.get("title") or "", text=_doc_text(rec, max_chars), facts_json=_facts_json(rec))
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    last_err: str | None = None
    for _ in range(2):
        try:
            return llm_client.extract_json(llm_client.chat(messages, max_tokens=8192))
        except (JsonParseError, LlmError) as e:
            last_err = str(e)
    raise LlmError(f"三组补全失败：{last_err}")


def _validate_fields(obj: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """16 字段校验与规范化；返回 (groups, problems)。缺字段/非法枚举兜底并记录。"""

    groups: dict[str, dict[str, Any]] = {}
    problems: list[str] = []
    for group, fields in config.FIELD_GROUPS.items():
        raw = obj.get(group) or {}
        out: dict[str, dict[str, Any]] = {}
        for field in fields:
            cell = raw.get(field)
            if not isinstance(cell, dict) or cell.get("value") in (None, ""):
                problems.append(f"{group}.{field} 缺失")
                out[field] = {"value": [] if field in config.LIST_FIELDS else "无", "confidence": None}
                continue
            value = cell["value"]
            if field in config.LIST_FIELDS and not isinstance(value, list):
                value = [value]
            confidence = llm_client.clamp_confidence(cell.get("confidence"))
            if field == "知识层次" and value not in config.KNOWLEDGE_LEVELS:
                problems.append(f"知识层次非法值：{value}")
                value = "无"
            if field == "价值观" and value not in config.VALUES_ORIENTATIONS:
                problems.append(f"价值观非法值：{value}")
                value = "中性"
            out[field] = {"value": value, "confidence": confidence}
        groups[group] = out
    return groups, problems


def _to_dataset_row(rec: dict[str, Any], groups: dict[str, dict[str, Any]],
                    fill_confidence: float | None, review_status: str) -> dict[str, Any]:
    """数据集行：字段取值（去置信度包装），对齐交付说明 §五样例。"""

    row: dict[str, Any] = {"docId": rec["docId"]}
    for group in ("structured", "basic", "related"):
        row[group] = {f: c["value"] for f, c in groups[group].items()}
    facts = rec.get("facts") or {}
    row["extractConfidence"] = facts.get("extractConfidence")
    row["fillConfidence"] = fill_confidence
    row["reviewStatus"] = review_status
    row["revisionStatus"] = "—" if review_status == "未进入复核" else "未修正"
    return row


def _process_doc(rec: dict[str, Any], threshold: float, max_chars: int) -> dict[str, Any]:
    try:
        obj = _fill_one(rec, max_chars)
    except LlmError as e:
        return {"failed": {"name": rec["docId"], "reason": str(e), "code": "model_call_failed"},
                "review": {"docId": rec["docId"], "fileName": rec.get("fileName"),
                           "fields": None, "code": "model_call_failed", "reviewReason": str(e)}}

    groups, problems = _validate_fields(obj)
    confidences = [c["confidence"] for g in groups.values() for c in g.values() if c["confidence"] is not None]
    fill_confidence = min(confidences) if confidences else None

    review_reasons = list(problems)
    if fill_confidence is None:
        review_reasons.append("逐字段置信度输出失败")
    elif fill_confidence < threshold:
        review_reasons.append("补全置信度低于阈值")

    review_status = "待复核" if review_reasons else "未进入复核"
    row = _to_dataset_row(rec, groups, fill_confidence, review_status)
    detail = {
        "docId": rec["docId"],
        "fileName": rec.get("fileName"),
        "fieldConfidences": {g: {f: c["confidence"] for f, c in cells.items()} for g, cells in groups.items()},
        "uncertain": obj.get("uncertain") or [],
        "problems": problems,
    }
    result: dict[str, Any] = {"record": row, "detail": detail}
    if review_reasons:
        code = review_codes.pick(
            (bool(problems), "field_invalid"),
            (fill_confidence is None, "confidence_missing"),
            (fill_confidence is not None and fill_confidence < threshold, "low_confidence"))
        result["review"] = {"docId": rec["docId"], "fileName": rec.get("fileName"),
                            "fields": groups, "code": code, "reviewReason": "；".join(review_reasons)}
    return result


def run(input_dir: Path, output_dir: Path, params: dict[str, Any], log) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    src = input_dir / RECORDS_FILE
    if not src.exists():
        raise ValueError(f"输入目录缺少 {RECORDS_FILE}（上游 meta_fact_extract 产物）")
    records = [json.loads(line) for line in src.read_text(encoding="utf-8").splitlines() if line.strip()]
    threshold = float(params["confidence_threshold"])
    max_chars = int(params["max_text_chars"])

    rows: list[dict[str, Any]] = []
    details: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    failed: list[dict[str, str]] = []
    lineage: list[dict[str, Any]] = []

    log("进入三组补全 %d 篇", len(records))
    results = llm_client.run_concurrent(
        records, lambda r: _process_doc(r, threshold, max_chars),
        concurrency=int(params["concurrency"]))

    for rec, outcome in zip(records, results):
        base = {"sample_id": rec["docId"], "source_file": rec.get("fileName")}
        if "failed" in outcome:
            failed.append(outcome["failed"])
            review.append(outcome["review"])
            lineage.append({**base, "action": "fail", "reason": outcome["failed"]["reason"]})
            continue
        rows.append(outcome["record"])
        details.append(outcome["detail"])
        lineage.append({**base, "action": "keep",
                        "metrics": {"fill_confidence": outcome["record"]["fillConfidence"]}})
        if "review" in outcome:
            review.append(outcome["review"])
            lineage.append({**base, "action": "review", "reason": outcome["review"]["reviewReason"]})

    for name, items in ((RECORDS_FILE, rows), (REVIEW_FILE, review), (DETAIL_FILE, details)):
        with (output_dir / name).open("w", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

    log("三组补全完成：数据集 %d 行（%d 篇待复核），%d 篇失败", len(rows), len(review) - len(failed), len(failed))
    return {
        "records_file": RECORDS_FILE,
        "summary": {
            "total": len(records), "filled": len(rows),
            "review": len(review), "failed": len(failed),
        },
        "skipped": [],
        "failed": failed,
        "review": review,
        "sample_lineage": lineage,
    }
