"""新闻体裁判定 · 算子核心（文本元信息 环节①，规则粗筛 + 大模型）。

输入：meta_clean_slice 的 records.jsonl（凭 inputFile 接续）。
规则粗筛过滤明显非新闻；模型负责边界判定。
置信度 <0.8 → 复核（不进下游）；≥0.8 非新闻 → 跳过；≥0.8 新闻 → 进下游。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .configs import config, prompts
from .utils import llm_client
from .utils.llm_client import JsonParseError, LlmError

OPERATOR_NAME = "新闻体裁判定"
ALLOWED_SUFFIXES = (".jsonl", ".zip")

PARAM_DEFAULTS: dict[str, Any] = {
    "confidence_threshold": config.CONFIDENCE_THRESHOLD,
    "concurrency": 4,
}

RECORDS_FILE = "records.jsonl"
REVIEW_FILE = "review.jsonl"

CATEGORIES = {"消息", "通讯", "特写", "专访", "通报", "评论", "广告", "教程", "通知", "其他"}


def validate_params(params: dict[str, Any]) -> dict[str, Any]:
    merged = {**PARAM_DEFAULTS, **(params or {})}
    if not (0.0 < float(merged["confidence_threshold"]) < 1.0):
        raise ValueError("confidence_threshold 须在 (0, 1) 之间")
    return merged


def _rule_screen(rec: dict[str, Any]) -> tuple[str, str] | None:
    """规则粗筛：命中明显非新闻特征返回 (原因, 码)，否则 None（交给模型）。"""

    title = rec.get("title") or ""
    text_head = "".join(s["text"] for s in rec.get("slices", []))[:config.FIRST_CHARS]
    if any(k in title for k in config.TUTORIAL_TITLE_KEYWORDS):
        return "规则粗筛-教程类", "rule_tutorial"
    if any(k in text_head for k in config.AD_KEYWORDS):
        return "规则粗筛-广告/产品页", "rule_ad_or_product"
    return None


def _judge_one(rec: dict[str, Any], threshold: float) -> dict[str, Any]:
    """模型判定单篇；返回 {record?, skip_reason?, review?} 三选一。"""

    text_head = "".join(s["text"] for s in rec.get("slices", []))[:config.FIRST_CHARS]
    user = prompts.GENRE_USER_TEMPLATE.format(
        title=rec.get("title") or "", source=rec.get("source") or "未知", text=text_head)
    messages = [
        {"role": "system", "content": prompts.GENRE_SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]
    last_err: str | None = None
    for _ in range(2):  # JSON 解析失败重试 1 次（传输重试由 llm_client 承担）
        try:
            obj = llm_client.extract_json(llm_client.chat(messages))
            break
        except (JsonParseError, LlmError) as e:
            last_err = str(e)
    else:
        return {"review": {**rec, "genre": None, "code": "model_output_invalid",
                           "reviewReason": f"模型输出解析失败：{last_err}"}}

    confidence = llm_client.clamp_confidence(obj.get("confidence"))
    genre = {
        "is_news": bool(obj.get("is_news")),
        "category": obj.get("category") if obj.get("category") in CATEGORIES else "其他",
        "conditions": obj.get("conditions") or {},
        "confidence": confidence,
        "reason": obj.get("reason"),
        "evidence": obj.get("evidence") or [],
        "screening": "model",
    }
    merged = {**rec, "genre": genre}
    if confidence is None or confidence < threshold:
        return {"review": {**merged, "code": "low_confidence",
                           "reviewReason": "体裁判定置信度低于阈值"}}
    if not genre["is_news"]:
        return {"skip_reason": "非新闻体裁", "skip_code": "non_news", "record": merged}
    return {"record": merged}


def run(input_dir: Path, output_dir: Path, params: dict[str, Any], log, progress=None) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    src = input_dir / RECORDS_FILE
    if not src.exists():
        raise ValueError(f"输入目录缺少 {RECORDS_FILE}（上游 meta_clean_slice 产物）")
    records = [json.loads(line) for line in src.read_text(encoding="utf-8").splitlines() if line.strip()]
    threshold = float(params["confidence_threshold"])

    kept: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    lineage: list[dict[str, Any]] = []

    to_model: list[dict[str, Any]] = []
    for rec in records:
        base = {"sample_id": rec["docId"], "source_file": rec.get("fileName")}
        screen = _rule_screen(rec)
        if screen:
            reason, code = screen
            skipped.append({"name": rec["docId"], "reason": reason, "code": code})
            lineage.append({**base, "action": "skip", "reason": reason})
        else:
            to_model.append(rec)

    log("规则粗筛跳过 %d 篇，进入模型判定 %d 篇", len(skipped), len(to_model))
    results = llm_client.run_concurrent(
        to_model, lambda r: _judge_one(r, threshold),
        concurrency=int(params["concurrency"]), progress=progress)

    for rec, outcome in zip(to_model, results):
        base = {"sample_id": rec["docId"], "source_file": rec.get("fileName")}
        if "review" in outcome:
            review.append(outcome["review"])
            lineage.append({**base, "action": "review", "reason": outcome["review"]["reviewReason"]})
        elif "skip_reason" in outcome:
            skipped.append({"name": rec["docId"], "reason": outcome["skip_reason"],
                            "code": outcome.get("skip_code", "non_news")})
            lineage.append({**base, "action": "skip", "reason": outcome["skip_reason"]})
        else:
            kept.append(outcome["record"])
            lineage.append({**base, "action": "keep",
                            "metrics": {"genre_confidence": outcome["record"]["genre"]["confidence"]}})

    for name, rows in ((RECORDS_FILE, kept), (REVIEW_FILE, review)):
        with (output_dir / name).open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    log("体裁判定完成：新闻 %d 篇，复核 %d 篇，跳过累计 %d 篇", len(kept), len(review), len(skipped))
    return {
        "records_file": RECORDS_FILE,
        "summary": {
            "total": len(records), "news": len(kept),
            "review": len(review), "skipped": len(skipped),
        },
        "skipped": skipped,
        "failed": [],
        "review": review,
        "sample_lineage": lineage,
    }
