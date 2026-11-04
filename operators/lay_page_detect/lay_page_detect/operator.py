"""逐页版面检测 · 算子核心（复杂版面 环节②③，视觉大模型逐页检测 + 规则分流 + 汇总）。

输入：lay_page_render 的 records.jsonl（含 pages 页图清单）。
流程：逐页视觉调用（并发 4–8）→ §4.6 后处理校验（非法则重试 1 次）
→ 规则分流（框选偏低/判定偏低/重叠 IoU>0.3/越界/顺序重号缺号/空页 → 进复核，不阻断）
→ 页图 + 框选图层可视化 → 一页一行数据集 + 复核/失败清单汇总（环节③ 不做自检）。
分流口径：模型调用失败/输出持续非法 → 失败页清单；规则命中 → 复核清单且保留数据集行。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .configs import config, prompts
from .utils import llm_client, review_codes
from .utils.llm_client import JsonParseError, LlmError

OPERATOR_NAME = "逐页版面检测"
ALLOWED_SUFFIXES = (".jsonl", ".zip")

PARAM_DEFAULTS: dict[str, Any] = {
    "confidence_threshold": config.CONFIDENCE_THRESHOLD,
    "iou_threshold": config.IOU_THRESHOLD,
    "concurrency": 4,
    "draw_overlay": True,
}

RECORDS_FILE = "records.jsonl"
REVIEW_FILE = "review.jsonl"
VISUAL_DIR = "visual"


def validate_params(params: dict[str, Any]) -> dict[str, Any]:
    merged = {**PARAM_DEFAULTS, **(params or {})}
    if not (0.0 < float(merged["confidence_threshold"]) < 1.0):
        raise ValueError("confidence_threshold 须在 (0, 1) 之间")
    if not (0.0 < float(merged["iou_threshold"]) < 1.0):
        raise ValueError("iou_threshold 须在 (0, 1) 之间")
    return merged


# ---------- 模型调用与 §4.6 后处理校验 ----------

class PageOutputError(LlmError):
    """页级输出非法（JSON 解析失败/pageNo 不符/类型越枚举/readingOrder 非正整数）。"""


def _validate_output(obj: Any, page_no: int) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise PageOutputError("输出不是 JSON 对象")
    if obj.get("pageNo") is None:
        obj["pageNo"] = page_no  # 模型偶发漏回填，页号本端已知，直接补齐
    elif obj["pageNo"] != page_no:
        raise PageOutputError(f"pageNo 不一致：期望 {page_no}，实得 {obj.get('pageNo')}")
    elements = obj.get("elements")
    if not isinstance(elements, list):
        raise PageOutputError("elements 缺失或不是数组")
    for e in elements:
        if e.get("type") not in config.ELEMENT_TYPES:
            raise PageOutputError(f"元素类型越枚举：{e.get('type')}")
        if not isinstance(e.get("readingOrder"), int) or e["readingOrder"] <= 0:
            raise PageOutputError(f"readingOrder 非正整数：{e.get('readingOrder')}")
    return obj


def _detect_page(image_path: Path, page_no: int) -> dict[str, Any]:
    """单页检测；输出非法重试 1 次（传输重试由 llm_client 承担）。"""

    user = prompts.DETECT_USER_TEMPLATE.format(pageNo=page_no)
    last_err: str | None = None
    for _ in range(2):
        try:
            obj = llm_client.extract_json(llm_client.chat_vision(
                prompts.DETECT_SYSTEM_PROMPT, user, image_path,
                max_tokens=4096, max_long_edge=config.IMAGE_MAX_LONG_EDGE))
            return _validate_output(obj, page_no)
        except (JsonParseError, LlmError) as e:
            last_err = str(e)
    raise PageOutputError(f"页 {page_no} 输出非法：{last_err}")


# ---------- 元素规范化与规则分流 ----------

def _normalize_elements(elements: list[dict[str, Any]], page_no: int) -> tuple[list[dict[str, Any]], bool]:
    """elementId 重写为 p{页}-e{序}；bbox 截断到 0–1000，返回 (elements, 是否发生越界修正)。"""

    out: list[dict[str, Any]] = []
    clipped = False
    for i, e in enumerate(elements, start=1):
        bbox = e.get("bbox") or [0, 0, 0, 0]
        fixed = []
        for j, v in enumerate(bbox[:4]):
            v = int(v)
            hi = 1000
            if v < 0 or v > hi:
                clipped = True
            fixed.append(max(0, min(hi, v)))
        if fixed[0] >= fixed[2]:
            fixed[2] = min(1000, fixed[0] + 1)
            clipped = True
        if fixed[1] >= fixed[3]:
            fixed[3] = min(1000, fixed[1] + 1)
            clipped = True
        out.append({
            "elementId": f"p{page_no}-e{i}",
            "type": e["type"],
            "bbox": fixed,
            "readingOrder": e["readingOrder"],
            "bboxConf": llm_client.clamp_confidence(e.get("bboxConf")),
            "typeConf": llm_client.clamp_confidence(e.get("typeConf")),
        })
    return out, clipped


def _iou(a: list[int], b: list[int]) -> float:
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    if inter <= 0:
        return 0.0
    area = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / area if area > 0 else 0.0


def _rule_route(elements: list[dict[str, Any]], clipped: bool,
                threshold: float, iou_threshold: float) -> tuple[list[str], str | None]:
    """六类分流规则，返回 (命中原因列表, 首个命中码)；原因列表为空 = 不进复核。"""

    reasons: list[str] = []
    if not elements:
        return ["空页"], "empty_page"
    bbox_low = [e for e in elements if (e["bboxConf"] or 0) < threshold]
    type_low = [e for e in elements if (e["typeConf"] or 0) < threshold]
    if bbox_low:
        reasons.append(f"框选偏低（{len(bbox_low)} 个）")
    if type_low:
        reasons.append(f"判定偏低（{len(type_low)} 个）")
    overlapped = False
    for i in range(len(elements)):
        for j in range(i + 1, len(elements)):
            if _iou(elements[i]["bbox"], elements[j]["bbox"]) > iou_threshold:
                reasons.append(f"重叠（{elements[i]['elementId']}×{elements[j]['elementId']} IoU>{iou_threshold}）")
                overlapped = True
                break
        else:
            continue
        break
    if clipped:
        reasons.append("越界（bbox 超出 0–1000，已截断）")
    orders = sorted(e["readingOrder"] for e in elements)
    order_conflict = orders != list(range(1, len(elements) + 1))
    if order_conflict:
        reasons.append("顺序冲突（重号或缺号）")
    code = review_codes.pick(
        (bool(bbox_low), "bbox_low_confidence"),
        (bool(type_low), "type_low_confidence"),
        (overlapped, "element_overlap"),
        (clipped, "bbox_out_of_bounds"),
        (order_conflict, "reading_order_conflict")) if reasons else None
    return reasons, code


def _draw_overlay(image_path: Path, elements: list[dict[str, Any]], out_path: Path) -> None:
    """页图 + 框选图层（复核可视化用）。"""

    from PIL import Image, ImageDraw

    img = Image.open(image_path).convert("RGB")
    w, h = img.size
    draw = ImageDraw.Draw(img)
    for e in elements:
        x1, y1, x2, y2 = (e["bbox"][0] / 1000 * w, e["bbox"][1] / 1000 * h,
                          e["bbox"][2] / 1000 * w, e["bbox"][3] / 1000 * h)
        draw.rectangle([x1, y1, x2, y2], outline=(230, 57, 70), width=2)
        draw.text((x1 + 2, y1 + 2), f"{e['elementId']}:{e['type']}", fill=(230, 57, 70))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)


def _process_page(doc: dict[str, Any], page: dict[str, Any], input_root: Path,
                  output_dir: Path, threshold: float, iou_threshold: float,
                  draw_overlay: bool) -> dict[str, Any]:
    page_no = page["pageNo"]
    page_id = f"{doc['docId']}-#{page_no}"
    image_path = input_root / page["image"]

    obj = _detect_page(image_path, page_no)
    elements, clipped = _normalize_elements(obj.get("elements") or [], page_no)
    reasons, code = _rule_route(elements, clipped, threshold, iou_threshold)

    overlay = None
    if draw_overlay and elements:
        overlay = f"{VISUAL_DIR}/{doc['docId']}_p{page_no:04d}.png"
        _draw_overlay(image_path, elements, output_dir / overlay)

    bbox_conf = min((e["bboxConf"] for e in elements if e["bboxConf"] is not None), default=None)
    type_conf = min((e["typeConf"] for e in elements if e["typeConf"] is not None), default=None)
    low_count = sum(1 for e in elements
                    for c in (e["bboxConf"], e["typeConf"]) if c is not None and c < threshold)

    row = {
        "pageId": page_id,
        "docId": doc["docId"],
        "pageNo": page_no,
        "image": page["image"],
        "overlay": overlay,
        "elementCount": len(elements),
        "elements": elements,
        "structureTree": obj.get("structureTree") or [],
        "readingOrder": [e["readingOrder"] for e in sorted(elements, key=lambda x: x["readingOrder"])],
        "confidence": {"bbox": bbox_conf, "type": type_conf},
        "lowConfidenceCount": low_count,
        "lowConfidenceReasons": "；".join(reasons),
        "reviewStatus": "待复核" if reasons else "未进入复核",
        "revisionStatus": "未修正" if reasons else "—",
    }
    result: dict[str, Any] = {"row": row}
    if reasons:
        result["review"] = {**row, "code": code, "reviewReason": "；".join(reasons)}
    return result


def run(input_dir: Path, output_dir: Path, params: dict[str, Any], log) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    src = input_dir / RECORDS_FILE
    if not src.exists():
        raise ValueError(f"输入目录缺少 {RECORDS_FILE}（上游 lay_page_render 产物）")
    docs = [json.loads(line) for line in src.read_text(encoding="utf-8").splitlines() if line.strip()]
    threshold = float(params["confidence_threshold"])
    iou_threshold = float(params["iou_threshold"])
    draw_overlay = bool(params["draw_overlay"])

    # 失败页清单：渲染失败页直接汇入（不送环节②）
    failed: list[dict[str, str]] = []
    tasks: list[tuple[dict, dict]] = []
    for doc in docs:
        for fp in doc.get("failedPages") or []:
            failed.append({"name": f"{doc['docId']}-#{fp['pageNo']}", "reason": fp["reason"],
                           "code": fp.get("code", "page_render_failed")})
        for page in doc.get("pages") or []:
            tasks.append((doc, page))

    rows: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    lineage: list[dict[str, Any]] = []

    log("进入逐页检测 %d 页（%d 份文档）", len(tasks), len(docs))

    def _work(task: tuple[dict, dict]) -> dict[str, Any]:
        doc, page = task
        try:
            return _process_page(doc, page, input_dir, output_dir,
                                 threshold, iou_threshold, draw_overlay)
        except LlmError as e:
            return {"error": f"{doc['docId']}-#{page['pageNo']}", "reason": str(e)}

    results = llm_client.run_concurrent(tasks, _work, concurrency=int(params["concurrency"]))

    for (doc, page), outcome in zip(tasks, results):
        page_id = f"{doc['docId']}-#{page['pageNo']}"
        base = {"sample_id": page_id, "source_file": doc.get("fileName")}
        if "error" in outcome:
            failed.append({"name": page_id, "reason": outcome["reason"], "code": "model_call_failed"})
            lineage.append({**base, "action": "fail", "reason": outcome["reason"]})
            continue
        rows.append(outcome["row"])
        if "review" in outcome:
            review.append(outcome["review"])
            lineage.append({**base, "action": "review", "reason": outcome["review"]["reviewReason"]})
        else:
            lineage.append({**base, "action": "keep",
                            "metrics": {"elements": outcome["row"]["elementCount"],
                                        "bbox_conf": outcome["row"]["confidence"]["bbox"],
                                        "type_conf": outcome["row"]["confidence"]["type"]}})

    rows.sort(key=lambda r: (r["docId"], r["pageNo"]))
    for name, items in ((RECORDS_FILE, rows), (REVIEW_FILE, review)):
        with (output_dir / name).open("w", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

    log("检测完成：%d 页入库（%d 页待复核），失败页累计 %d 页", len(rows), len(review), len(failed))
    return {
        "records_file": RECORDS_FILE,
        "summary": {
            "docs": len(docs), "pages": len(tasks), "detected": len(rows),
            "review": len(review), "failedPages": len(failed),
        },
        "skipped": [],
        "failed": failed,
        "review": review,
        "sample_lineage": lineage,
    }
