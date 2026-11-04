"""新闻事实抽取 · 算子核心（文本元信息 环节②，文本大模型按片抽取 + 合并去重）。

输入：meta_genre_judge 的 records.jsonl（仅新闻文档，含 slices）。
流程：逐片抽取（source_type/time_candidates/entities/conflicts/uncertain）
→ 文档级合并：时间按值去重、实体按 mention 去重、多值标 conflict
→ 复核分流：抽取全部失败 → 仅复核不进下游；来源缺失/时间冲突/低置信 → 复核 + 继续下游（冲突不阻断，见交付说明 §4.2）。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .configs import config, prompts
from .utils import llm_client, review_codes
from .utils.llm_client import JsonParseError, LlmError

OPERATOR_NAME = "新闻事实抽取"
ALLOWED_SUFFIXES = (".jsonl", ".zip")

PARAM_DEFAULTS: dict[str, Any] = {
    "confidence_threshold": config.EXTRACTION_CONFIDENCE_THRESHOLD,
    "concurrency": 4,
}

RECORDS_FILE = "records.jsonl"
REVIEW_FILE = "review.jsonl"

ENTITY_KINDS = {"person", "place", "org"}


def validate_params(params: dict[str, Any]) -> dict[str, Any]:
    merged = {**PARAM_DEFAULTS, **(params or {})}
    if not (0.0 < float(merged["confidence_threshold"]) < 1.0):
        raise ValueError("confidence_threshold 须在 (0, 1) 之间")
    return merged


def _extract_slice(title: str, slice_: dict[str, Any]) -> dict[str, Any]:
    """单片抽取；JSON 解析失败重试 1 次（传输重试由 llm_client 承担）。"""

    user = prompts.FACT_USER_TEMPLATE.format(title=title or "", text=slice_["text"])
    messages = [
        {"role": "system", "content": prompts.FACT_SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]
    last_err: str | None = None
    for _ in range(2):
        try:
            return llm_client.extract_json(llm_client.chat(messages))
        except (JsonParseError, LlmError) as e:
            last_err = str(e)
    raise LlmError(f"切片 {slice_['sliceId']} 抽取失败：{last_err}")


def _clamp(value: Any) -> float | None:
    return llm_client.clamp_confidence(value)


def _normalize_slice_result(obj: dict[str, Any], slice_id: str) -> dict[str, Any]:
    """模型输出规范化：置信度截断、枚举兜底、缺省补空。"""

    st = obj.get("source_type") or {}
    source_type = {
        "value": st.get("value") if st.get("value") in config.SOURCE_TYPES else None,
        "evidence": st.get("evidence"),
        "confidence": _clamp(st.get("confidence")),
    }
    times = []
    for t in obj.get("time_candidates") or []:
        if not t.get("value"):
            continue
        times.append({
            "value": str(t["value"]), "granularity": t.get("granularity"),
            "evidence": t.get("evidence"), "position": t.get("position"),
            "confidence": _clamp(t.get("confidence")), "sliceId": slice_id,
        })
    entities = []
    for e in obj.get("entities") or []:
        if not e.get("mention"):
            continue
        entities.append({
            "mention": str(e["mention"]),
            "kind": e.get("kind") if e.get("kind") in ENTITY_KINDS else "org",
            "evidence": e.get("evidence"), "position": e.get("position"),
            "confidence": _clamp(e.get("confidence")), "sliceId": slice_id,
        })
    return {
        "source_type": source_type,
        "time_candidates": times,
        "entities": entities,
        "conflicts": obj.get("conflicts") or [],
        "uncertain": obj.get("uncertain") or [],
    }


def _merge_facts(per_slice: list[dict[str, Any]]) -> dict[str, Any]:
    """文档级合并：时间按值去重、实体按 mention 去重、多值生成 conflict。"""

    # 来源类型：按值去重保留最高置信；多个不同值 → conflict
    st_by_value: dict[str, dict[str, Any]] = {}
    for s in per_slice:
        st = s["source_type"]
        if st["value"] and (st["value"] not in st_by_value
                            or (st["confidence"] or 0) > (st_by_value[st["value"]]["confidence"] or 0)):
            st_by_value[st["value"]] = st
    source_type = max(st_by_value.values(), key=lambda x: x["confidence"] or 0, default=None)

    # 时间候选：按值去重保留最高置信
    t_by_value: dict[str, dict[str, Any]] = {}
    for s in per_slice:
        for t in s["time_candidates"]:
            if t["value"] not in t_by_value or (t["confidence"] or 0) > (t_by_value[t["value"]]["confidence"] or 0):
                t_by_value[t["value"]] = t
    time_candidates = list(t_by_value.values())

    # 实体：按 mention 去重；同名不同 kind 记入 uncertain
    e_by_mention: dict[str, dict[str, Any]] = {}
    uncertain: list[str] = []
    for s in per_slice:
        uncertain.extend(s["uncertain"])
        for e in s["entities"]:
            prev = e_by_mention.get(e["mention"])
            if prev is None:
                e_by_mention[e["mention"]] = e
            else:
                if prev["kind"] != e["kind"]:
                    uncertain.append(f"实体「{e['mention']}」类型不一致：{prev['kind']} / {e['kind']}")
                if (e["confidence"] or 0) > (prev["confidence"] or 0):
                    e_by_mention[e["mention"]] = e
    entities = list(e_by_mention.values())

    # 冲突：模型自报 + 合并生成（去重）
    conflicts: list[dict[str, Any]] = []
    seen: set[tuple] = set()
    for s in per_slice:
        for c in s["conflicts"]:
            key = (c.get("field"), tuple(sorted(c.get("candidates") or [])))
            if key not in seen:
                seen.add(key)
                conflicts.append(c)
    if len(time_candidates) > 1:
        key = ("time", tuple(sorted(t["value"] for t in time_candidates)))
        if key not in seen:
            conflicts.append({
                "field": "time",
                "candidates": [t["value"] for t in time_candidates],
                "reason": "多切片时间候选不一致",
            })
    if len(st_by_value) > 1:
        key = ("source_type", tuple(sorted(st_by_value)))
        if key not in seen:
            conflicts.append({
                "field": "source_type",
                "candidates": sorted(st_by_value),
                "reason": "多切片来源类型不一致",
            })

    # 抽取置信度 = 来源/时间/实体最低分（交付说明 §五）
    scores = [c for c in ([source_type and source_type["confidence"]]
                          + [t["confidence"] for t in time_candidates]
                          + [e["confidence"] for e in entities]) if c is not None]
    extract_confidence = min(scores) if scores else None

    return {
        "sourceType": source_type,
        "timeCandidates": time_candidates,
        "entities": entities,
        "conflicts": conflicts,
        "uncertain": sorted(set(uncertain)),
        "extractConfidence": extract_confidence,
    }


def _process_doc(rec: dict[str, Any], threshold: float) -> dict[str, Any]:
    """单文档：逐片抽取 → 合并 → 复核分流。返回 {record?, review?, review_reasons}。"""

    per_slice: list[dict[str, Any]] = []
    slice_errors: list[str] = []
    for s in rec.get("slices", []):
        try:
            per_slice.append(_normalize_slice_result(_extract_slice(rec.get("title"), s), s["sliceId"]))
        except LlmError as e:
            slice_errors.append(str(e))

    base = {"docId": rec["docId"], "fileName": rec.get("fileName")}
    if not per_slice:
        return {"review": {**rec, "facts": None, "code": "model_call_failed",
                           "reviewReason": "事实抽取失败：全部切片模型调用失败；" + "；".join(slice_errors)}}

    facts = _merge_facts(per_slice)
    if slice_errors:
        facts["uncertain"].append(f"{len(slice_errors)} 个切片抽取失败，结果基于其余切片")
    merged = {**rec, "facts": facts}

    review_reasons: list[str] = []
    if facts["sourceType"] is None:
        review_reasons.append("来源类型缺失")
    if facts["conflicts"]:
        review_reasons.append("候选冲突待裁定：" + "、".join(c["field"] for c in facts["conflicts"]))
    if facts["extractConfidence"] is not None and facts["extractConfidence"] < threshold:
        review_reasons.append("抽取置信度低于阈值")
    # 冲突不阻断（交付说明 §4.2）：进复核同时继续下游
    result: dict[str, Any] = {"record": merged}
    if review_reasons:
        code = review_codes.pick(
            (facts["sourceType"] is None, "source_type_missing"),
            (bool(facts["conflicts"]), "candidate_conflict"),
            (facts["extractConfidence"] is not None and facts["extractConfidence"] < threshold,
             "low_confidence"))
        result["review"] = {**merged, "code": code, "reviewReason": "；".join(review_reasons)}
    return result


def run(input_dir: Path, output_dir: Path, params: dict[str, Any], log, progress=None) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    src = input_dir / RECORDS_FILE
    if not src.exists():
        raise ValueError(f"输入目录缺少 {RECORDS_FILE}（上游 meta_genre_judge 产物）")
    records = [json.loads(line) for line in src.read_text(encoding="utf-8").splitlines() if line.strip()]
    threshold = float(params["confidence_threshold"])

    kept: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    failed: list[dict[str, str]] = []
    lineage: list[dict[str, Any]] = []

    log("进入事实抽取 %d 篇", len(records))
    results = llm_client.run_concurrent(
        records, lambda r: _process_doc(r, threshold),
        concurrency=int(params["concurrency"]), progress=progress)

    for rec, outcome in zip(records, results):
        base = {"sample_id": rec["docId"], "source_file": rec.get("fileName")}
        if "record" in outcome:
            kept.append(outcome["record"])
            facts = outcome["record"]["facts"]
            lineage.append({**base, "action": "keep",
                            "metrics": {"extract_confidence": facts["extractConfidence"],
                                        "entities": len(facts["entities"]),
                                        "conflicts": len(facts["conflicts"])}})
        else:
            failed.append({"name": rec["docId"], "reason": outcome["review"]["reviewReason"],
                           "code": outcome["review"].get("code", "model_call_failed")})
            lineage.append({**base, "action": "fail", "reason": outcome["review"]["reviewReason"]})
        if "review" in outcome:
            review.append(outcome["review"])
            if "record" in outcome:
                lineage.append({**base, "action": "review", "reason": outcome["review"]["reviewReason"]})

    for name, rows in ((RECORDS_FILE, kept), (REVIEW_FILE, review)):
        with (output_dir / name).open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    log("事实抽取完成：%d 篇通过（%d 篇待复核），%d 篇失败", len(kept), len(review) - len(failed), len(failed))
    return {
        "records_file": RECORDS_FILE,
        "summary": {
            "total": len(records), "extracted": len(kept),
            "review": len(review), "failed": len(failed),
        },
        "skipped": [],
        "failed": failed,
        "review": review,
        "sample_lineage": lineage,
    }
