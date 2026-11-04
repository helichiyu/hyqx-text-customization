"""图文要素与描述生成 · 算子核心（图文融合 环节②③，按判型选 Prompt 一次调用 + 回核 + 汇总）。

输入：img_type_classify 的 records.jsonl（含 imageType）。
流程：按大类选 4 套 Prompt 之一，一次调用出 OCR/要素/描述/逐字段置信度（§4.3.8）
→ §4.3.7 校验（JSON/type/subtype 枚举 → 重试；缺描述字段/缺字段置信度 → 进复核）
→ 回核（环节③#2：描述中的数字须能在 OCR 文字中找到依据，否则进复核）
→ 三个置信度（判型/OCR 最低/描述最低）任一 <0.8 → 进复核，保留数据集行。
模型调用失败 → 失败清单 + 复核，不进数据集。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .configs import config, prompts
from .utils import llm_client, review_codes
from .utils.llm_client import JsonParseError, LlmError

OPERATOR_NAME = "图文要素与描述生成"
ALLOWED_SUFFIXES = (".jsonl", ".zip")

PARAM_DEFAULTS: dict[str, Any] = {
    "confidence_threshold": config.CONFIDENCE_THRESHOLD,
    "concurrency": 4,
}

RECORDS_FILE = "records.jsonl"
REVIEW_FILE = "review.jsonl"

_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")


def validate_params(params: dict[str, Any]) -> dict[str, Any]:
    merged = {**PARAM_DEFAULTS, **(params or {})}
    if not (0.0 < float(merged["confidence_threshold"]) < 1.0):
        raise ValueError("confidence_threshold 须在 (0, 1) 之间")
    return merged


class DescribeOutputError(LlmError):
    """描述输出非法（JSON 解析失败 / type/subtype 与判型不符）。"""


def _describe_one(rec: dict[str, Any], no: int, input_root: Path) -> dict[str, Any]:
    category = rec["imageType"]["category"]
    spec = config.CATEGORY_SPEC[category]
    system, user_tpl = prompts.CATEGORY_PROMPTS[category]
    user = user_tpl.format(no=no)
    last_err: str | None = None
    for _ in range(2):
        try:
            obj = llm_client.extract_json(llm_client.chat_vision(
                system, user, input_root / rec["image"],
                max_tokens=4096, max_long_edge=config.IMAGE_MAX_LONG_EDGE))
            if obj.get("type") != spec["type"] or obj.get("subtype") != rec["imageType"]["subtype"]:
                raise DescribeOutputError(
                    f"type/subtype 与判型不符：{obj.get('type')}/{obj.get('subtype')}"
                    f" ≠ {spec['type']}/{rec['imageType']['subtype']}")
            return obj
        except (JsonParseError, LlmError) as e:
            last_err = str(e)
    raise DescribeOutputError(f"描述生成失败：{last_err}")


def _verify_numbers(description: dict[str, str], ocr: list[dict[str, Any]]) -> list[str]:
    """回核（环节③#2）：描述中的数字须能在 OCR 文字中找到依据，返回无依据数字清单。"""

    ocr_text = "".join(str(b.get("text") or "") for b in ocr)
    unsupported: list[str] = []
    for field, text in description.items():
        for num in _NUMBER_RE.findall(str(text)):
            if num not in ocr_text and num not in ("1", "2"):  # 序号性 1/2 段不计
                unsupported.append(f"{field}：{num}")
    return unsupported


def _process(rec: dict[str, Any], no: int, input_root: Path, threshold: float) -> dict[str, Any]:
    image_id = rec["imageId"]
    category = rec["imageType"]["category"]
    spec = config.CATEGORY_SPEC[category]

    try:
        obj = _describe_one(rec, no, input_root)
    except DescribeOutputError as e:
        return {"failed": {"name": image_id, "reason": str(e), "code": "model_call_failed"},
                "review": {"imageId": image_id, "fileName": rec.get("fileName"),
                           "description": None, "code": "model_call_failed", "reviewReason": str(e)}}

    reasons: list[str] = []
    missing_fields = False
    description = obj.get("description") or {}
    for field in spec["fields"]:
        if field not in description or description[field] in (None, ""):
            missing_fields = True
            reasons.append(f"描述缺字段：{field}")
            description[field] = "无"
    description = {f: str(description[f]) for f in spec["fields"]}

    field_conf_raw = obj.get("fieldConfidence") or {}
    field_conf: dict[str, float | None] = {}
    missing_confidence = False
    for field in spec["fields"]:
        conf = llm_client.clamp_confidence(field_conf_raw.get(field))
        if conf is None:
            missing_confidence = True
            reasons.append(f"字段置信度缺失：{field}")
        field_conf[field] = conf

    ocr = [{"text": str(b.get("text")), "conf": llm_client.clamp_confidence(b.get("conf"))}
           for b in (obj.get("ocr") or []) if isinstance(b, dict) and b.get("text")]
    ocr_conf = min((b["conf"] for b in ocr if b["conf"] is not None), default=None)
    desc_conf_values = [c for c in field_conf.values() if c is not None]
    desc_conf = min(desc_conf_values) if desc_conf_values else None
    type_conf = (rec.get("imageType") or {}).get("confidence")

    unsupported = _verify_numbers(description, ocr)
    if unsupported:
        reasons.append("回核无依据内容：" + "、".join(unsupported[:5]))

    low_items = []
    low_type = type_conf is not None and type_conf < threshold
    low_ocr = ocr_conf is not None and ocr_conf < threshold
    low_desc = desc_conf is not None and desc_conf < threshold
    if low_type:
        low_items.append("判型偏低")
    if low_ocr:
        low_items.append("OCR 偏低")
    if low_desc:
        low_items.append("描述偏低")
    reasons.extend(low_items)

    row = {
        "imageId": image_id,
        "type": category,
        "subtype": rec["imageType"]["subtype"],
        "table": obj.get("table") if category == "表格" else None,
        "description": description,
        "confidence": {"type": type_conf, "ocr": ocr_conf, "desc": desc_conf},
        "lowConfidenceCount": len(low_items),
        "lowConfidenceReasons": "；".join(reasons),
        "reviewStatus": "待复核" if reasons else "未进入复核",
        "revisionStatus": "未修正" if reasons else "—",
    }
    # 复核/查看用明细：OCR 明细、结构要素、不确定项（不进数据集字段口径外单列文件）
    detail = {
        "imageId": image_id, "fileName": rec.get("fileName"), "image": rec.get("image"),
        "ocr": ocr, "fieldConfidence": field_conf,
        "elements": {k: obj.get(k) for k in ("axis", "legends", "series", "nodes", "edges") if obj.get(k) is not None},
        "uncertain": obj.get("uncertain") or [],
    }
    result: dict[str, Any] = {"row": row, "detail": detail}
    if reasons:
        code = review_codes.pick(
            (missing_fields, "missing_fields"),
            (bool(unsupported), "unverified_numbers"),
            (missing_confidence, "missing_confidence"),
            (low_type, "low_type_confidence"),
            (low_ocr, "low_ocr_confidence"),
            (low_desc, "low_desc_confidence"))
        result["review"] = {**row, "code": code, "reviewReason": "；".join(reasons)}
    return result


DETAIL_FILE = "details.jsonl"


def run(input_dir: Path, output_dir: Path, params: dict[str, Any], log, progress=None) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    src = input_dir / RECORDS_FILE
    if not src.exists():
        raise ValueError(f"输入目录缺少 {RECORDS_FILE}（上游 img_type_classify 产物）")
    records = [json.loads(line) for line in src.read_text(encoding="utf-8").splitlines() if line.strip()]
    threshold = float(params["confidence_threshold"])

    rows: list[dict[str, Any]] = []
    details: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    failed: list[dict[str, str]] = []
    lineage: list[dict[str, Any]] = []

    log("进入要素与描述生成 %d 张", len(records))
    results = llm_client.run_concurrent(
        list(enumerate(records, start=1)),
        lambda item: _process(item[1], item[0], input_dir, threshold),
        concurrency=int(params["concurrency"]), progress=progress)

    for rec, outcome in zip(records, results):
        base = {"sample_id": rec["imageId"], "source_file": rec.get("fileName")}
        if "failed" in outcome:
            failed.append(outcome["failed"])
            review.append(outcome["review"])
            lineage.append({**base, "action": "fail", "reason": outcome["failed"]["reason"]})
            continue
        rows.append(outcome["row"])
        details.append(outcome["detail"])
        if "review" in outcome:
            review.append(outcome["review"])
            lineage.append({**base, "action": "review", "reason": outcome["review"]["reviewReason"]})
        else:
            lineage.append({**base, "action": "keep",
                            "metrics": {"desc_confidence": outcome["row"]["confidence"]["desc"]}})

    for name, items in ((RECORDS_FILE, rows), (REVIEW_FILE, review), (DETAIL_FILE, details)):
        with (output_dir / name).open("w", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

    log("描述生成完成：数据集 %d 行（%d 张待复核），%d 张失败", len(rows), len(review) - len(failed), len(failed))
    return {
        "records_file": RECORDS_FILE,
        "summary": {
            "total": len(records), "described": len(rows),
            "review": len(review), "failed": len(failed),
        },
        "skipped": [],
        "failed": failed,
        "review": review,
        "sample_lineage": lineage,
    }
