"""图片判型 · 算子核心（图文融合 环节①#3#4，视觉模型）。

输入：img_region_locate 的 records.jsonl + predict 参数 category（任务大类）。
流程：逐张调用判型 Prompt → match=false 跳过（大类不一致）→ match=true 进下游；
判型置信度 <0.8 → 进复核（继续下游）；输出非法重试 1 次，模型失败 → 失败清单 + 复核。
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .configs import config, prompts
from .utils import llm_client
from .utils.llm_client import JsonParseError, LlmError

OPERATOR_NAME = "图片判型"
ALLOWED_SUFFIXES = (".jsonl", ".zip")

PARAM_DEFAULTS: dict[str, Any] = {
    "category": None,  # 必填：任务大类（几何/统计/表格/示意）
    "confidence_threshold": config.CONFIDENCE_THRESHOLD,
    "concurrency": 4,
}

RECORDS_FILE = "records.jsonl"
REVIEW_FILE = "review.jsonl"


def validate_params(params: dict[str, Any]) -> dict[str, Any]:
    merged = {**PARAM_DEFAULTS, **(params or {})}
    if merged["category"] not in config.CATEGORY_SUBTYPES:
        raise ValueError(f"category 必填且须为：{'/'.join(config.CATEGORY_SUBTYPES)}")
    if not (0.0 < float(merged["confidence_threshold"]) < 1.0):
        raise ValueError("confidence_threshold 须在 (0, 1) 之间")
    return merged


class ClassifyOutputError(LlmError):
    """判型输出非法（JSON 解析失败 / 大类或子类越枚举）。"""


def _validate(obj: Any) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise ClassifyOutputError("输出不是 JSON 对象")
    category = obj.get("category")
    if category not in config.CATEGORY_SUBTYPES:
        raise ClassifyOutputError(f"大类越枚举：{category}")
    subtype = obj.get("subtype")
    if subtype not in config.CATEGORY_SUBTYPES[category]:
        raise ClassifyOutputError(f"子类越枚举：{category}/{subtype}")
    if not isinstance(obj.get("match"), bool):
        raise ClassifyOutputError("match 缺失或不是布尔")
    return obj


def _classify_one(rec: dict[str, Any], no: int, task_category: str,
                  input_root: Path) -> dict[str, Any]:
    user = prompts.CLASSIFY_USER_TEMPLATE.format(category=task_category, no=no)
    last_err: str | None = None
    for _ in range(2):
        try:
            return _validate(llm_client.extract_json(llm_client.chat_vision(
                prompts.CLASSIFY_SYSTEM_PROMPT, user, input_root / rec["image"],
                max_tokens=1024, max_long_edge=config.IMAGE_MAX_LONG_EDGE)))
        except (JsonParseError, LlmError) as e:
            last_err = str(e)
    raise ClassifyOutputError(f"判型失败：{last_err}")


def run(input_dir: Path, output_dir: Path, params: dict[str, Any], log, progress=None) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    src = input_dir / RECORDS_FILE
    if not src.exists():
        raise ValueError(f"输入目录缺少 {RECORDS_FILE}（上游 img_region_locate 产物）")
    records = [json.loads(line) for line in src.read_text(encoding="utf-8").splitlines() if line.strip()]
    task_category = params["category"]
    threshold = float(params["confidence_threshold"])

    kept: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    failed: list[dict[str, str]] = []
    lineage: list[dict[str, Any]] = []

    log("进入判型 %d 张（任务大类：%s）", len(records), task_category)

    def _work(item: tuple[int, dict]) -> dict[str, Any]:
        no, rec = item
        try:
            obj = _classify_one(rec, no, task_category, input_dir)
        except ClassifyOutputError as e:
            return {"failed": {"name": rec["imageId"], "reason": str(e), "code": "model_call_failed"},
                    "review": {"imageId": rec["imageId"], "fileName": rec.get("fileName"),
                               "imageType": None, "code": "model_call_failed", "reviewReason": str(e)}}
        image_type = {
            "match": obj["match"],
            "category": obj["category"],
            "subtype": obj["subtype"],
            "confidence": llm_client.clamp_confidence(obj.get("confidence")),
            "reason": obj.get("reason"),
            "taskCategory": task_category,
        }
        # 规则兜底：模型 match=true 但 category 与任务大类矛盾时按不一致处理
        #（Qwen3-VL-8B 实测 2026-11-09 偶发自相矛盾；32B 未见）
        if not image_type["match"] or obj["category"] != task_category:
            return {"skip": {"name": rec["imageId"], "code": "category_mismatch",
                             "reason": f"大类不一致（任务={task_category}，实判={obj['category']}）"}}
        merged = {**rec, "imageType": image_type}
        result: dict[str, Any] = {"record": merged}
        conf = image_type["confidence"]
        if conf is None or conf < threshold:
            result["review"] = {**merged, "code": "low_confidence",
                                "reviewReason": "判型置信度低于阈值"}
        return result

    results = llm_client.run_concurrent(
        list(enumerate(records, start=1)), _work, concurrency=int(params["concurrency"]), progress=progress)

    for rec, outcome in zip(records, results):
        base = {"sample_id": rec["imageId"], "source_file": rec.get("fileName")}
        if "failed" in outcome:
            failed.append(outcome["failed"])
            review.append(outcome["review"])
            lineage.append({**base, "action": "fail", "reason": outcome["failed"]["reason"]})
        elif "skip" in outcome:
            skipped.append(outcome["skip"])
            lineage.append({**base, "action": "skip", "reason": outcome["skip"]["reason"]})
        else:
            kept.append(outcome["record"])
            # 输出目录自包含：匹配图片随记录复制，下游 describe 直接从本目录取图
            src_img = input_dir / rec["image"]
            dst_img = output_dir / rec["image"]
            if src_img != dst_img:
                dst_img.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_img, dst_img)
            if "review" in outcome:
                review.append(outcome["review"])
                lineage.append({**base, "action": "review", "reason": outcome["review"]["reviewReason"]})
            else:
                lineage.append({**base, "action": "keep",
                                "metrics": {"type_confidence": outcome["record"]["imageType"]["confidence"]}})

    for name, rows in ((RECORDS_FILE, kept), (REVIEW_FILE, review)):
        with (output_dir / name).open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    log("判型完成：%d 张匹配进下游，%d 张跳过，%d 张失败", len(kept), len(skipped), len(failed))
    return {
        "records_file": RECORDS_FILE,
        "summary": {
            "total": len(records), "matched": len(kept),
            "skipped": len(skipped), "review": len(review), "failed": len(failed),
        },
        "skipped": skipped,
        "failed": failed,
        "review": review,
        "sample_lineage": lineage,
    }
