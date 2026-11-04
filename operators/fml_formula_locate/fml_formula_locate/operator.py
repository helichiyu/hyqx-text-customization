"""公式区域定位与裁切 · 算子核心（公式文本 环节①，渲染 + 视觉 grounding + 裁切登记）。

流程：打开 PDF（加密/损坏/0 页 → 失败清单）→ 逐页渲染 → VLM 定位独立成行/带编号公式
→ 坐标校验（越界/面积过小 → 跳过并记录）→ 裁切公式图 → 抽取上下文文本（前后各 1–2 段，≤2000 字）
→ 登记 FormulaInstance（页码、bbox、裁切图、上下文）。
单页定位失败 → 跳过该页并记录；整份 0 公式 → failed（任务待处理口径）。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pymupdf
from PIL import Image

from .configs import config, prompts
from .utils import llm_client, pdf_utils, review_codes
from .utils.llm_client import JsonParseError, LlmError
from .utils.pdf_utils import PdfError

OPERATOR_NAME = "公式区域定位与裁切"
ALLOWED_SUFFIXES = (".pdf", ".zip")

PARAM_DEFAULTS: dict[str, Any] = {
    "dpi": config.RENDER_DPI,
    "max_context_chars": config.MAX_CONTEXT_CHARS,
    "concurrency": 4,
}

RECORDS_FILE = "records.jsonl"
CROPS_DIR = "crops"
PAGES_DIR = "pages"


def validate_params(params: dict[str, Any]) -> dict[str, Any]:
    merged = {**PARAM_DEFAULTS, **(params or {})}
    if not (72 <= int(merged["dpi"]) <= 300):
        raise ValueError("dpi 须在 72–300 之间")
    if int(merged["max_context_chars"]) < 200:
        raise ValueError("max_context_chars 须 ≥200")
    return merged


# ---------- 页文本与上下文 ----------

def _page_text_blocks(doc: pymupdf.Document, page_no: int) -> tuple[list[dict[str, Any]], str | None]:
    """提取页文本块（y 序，0–1000 归一化）与章节标题候选（全页最大字号文本）。"""

    page = doc.load_page(page_no - 1)
    rect = page.rect
    sx = 1000 / rect.width if rect.width else 1
    sy = 1000 / rect.height if rect.height else 1
    blocks: list[dict[str, Any]] = []
    chapter: str | None = None
    max_size = 0.0
    for b in page.get_text("dict").get("blocks", []):
        if b.get("type") != 0:
            continue
        text = "".join(s["text"] for line in b.get("lines", []) for s in line.get("spans", [])).strip()
        if not text:
            continue
        x0, y0, x1, y1 = b["bbox"]
        blocks.append({"y0": y0 * sy, "y1": y1 * sy, "text": text})
        size = max((s["size"] for line in b.get("lines", []) for s in line.get("spans", [])), default=0)
        if size > max_size and len(text) <= 60:
            max_size, chapter = size, text
    blocks.sort(key=lambda b: b["y0"])
    return blocks, chapter


def _context_for(blocks: list[dict[str, Any]], bbox: list[int], max_chars: int) -> str:
    """取公式前后各 1–2 段文本，总长 ≤max_chars。"""

    if not blocks:
        return ""
    fy0, fy1 = bbox[1], bbox[3]
    # 找与公式纵向重叠或最近的块索引
    idx = min(range(len(blocks)),
              key=lambda i: 0 if blocks[i]["y0"] <= (fy0 + fy1) / 2 <= blocks[i]["y1"]
              else min(abs(blocks[i]["y1"] - fy0), abs(blocks[i]["y0"] - fy1)))
    # 从最近块向前后各扩至多 2 段，总长 ≤max_chars
    parts: list[str] = []
    total = 0
    for i in range(max(0, idx - 2), min(len(blocks), idx + 3)):
        t = blocks[i]["text"]
        if total + len(t) > max_chars and parts:
            break
        parts.append(t)
        total += len(t)
    return "\n".join(parts)[:max_chars]


# ---------- 定位与裁切 ----------

def _locate_page(image_path: Path, page_no: int) -> list[dict[str, Any]]:
    """单页定位；输出非法重试 1 次（传输重试由 llm_client 承担）。"""

    user = prompts.LOCATE_USER_TEMPLATE.format(pageNo=page_no)
    last_err: str | None = None
    for _ in range(2):
        try:
            obj = llm_client.extract_json(llm_client.chat_vision(
                prompts.LOCATE_SYSTEM_PROMPT, user, image_path,
                max_tokens=2048, max_long_edge=config.IMAGE_MAX_LONG_EDGE))
            formulas = obj.get("formulas")
            if not isinstance(formulas, list):
                raise JsonParseError("formulas 缺失或不是数组")
            return formulas
        except (JsonParseError, LlmError) as e:
            last_err = str(e)
    raise LlmError(f"页 {page_no} 定位失败：{last_err}")


def _valid_bbox(bbox: Any) -> list[int] | None:
    """bbox 校验：四值、0–1000、x1<x2、y1<y2、面积 ≥ 阈值；非法返回 None。"""

    try:
        box = [int(v) for v in bbox[:4]]
    except (TypeError, ValueError):
        return None
    x1, y1, x2, y2 = box
    if not (0 <= x1 < x2 <= 1000 and 0 <= y1 < y2 <= 1000):
        return None
    if (x2 - x1) * (y2 - y1) < config.MIN_BBOX_AREA:
        return None
    return box


def _crop(page_image: Path, bbox: list[int], out_path: Path) -> tuple[int, int, int, int]:
    """按 0–1000 归一化 bbox 裁切，返回像素坐标 (x1, y1, x2, y2)。"""

    img = Image.open(page_image)
    w, h = img.size
    x1, y1 = int(bbox[0] / 1000 * w), int(bbox[1] / 1000 * h)
    x2, y2 = min(w, int(bbox[2] / 1000 * w) + 1), min(h, int(bbox[3] / 1000 * h) + 1)
    if x2 - x1 < 2 or y2 - y1 < 2:
        raise ValueError(f"裁切区域过小：{bbox} → ({x1},{y1},{x2},{y2})")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.crop((x1, y1, x2, y2)).save(out_path)
    return x1, y1, x2, y2


def _process_doc(pdf_path: Path, output_dir: Path, params: dict[str, Any], log) -> dict[str, Any]:
    doc_id = pdf_path.stem
    pages_dir = output_dir / PAGES_DIR / doc_id
    pages_dir.mkdir(parents=True, exist_ok=True)

    skipped: list[dict[str, str]] = []
    instances: list[dict[str, Any]] = []
    with pdf_utils.open_pdf(pdf_path) as doc:
        page_count = doc.page_count
        blocks_by_page: dict[int, tuple[list, str | None]] = {}
        # 逐页渲染
        page_images: dict[int, Path] = {}
        matrix = pymupdf.Matrix(int(params["dpi"]) / 72.0, int(params["dpi"]) / 72.0)
        for i in range(page_count):
            page_no = i + 1
            image_path = pages_dir / f"{doc_id}_p{page_no:04d}.png"
            try:
                pix = doc.load_page(i).get_pixmap(matrix=matrix)
                pix.save(image_path)
                page_images[page_no] = image_path
            except Exception as e:
                skipped.append({"name": f"{doc_id}-#{page_no}", "reason": f"渲染失败：{type(e).__name__}: {e}",
                                "code": "page_render_failed"})

    def _locate_one(page_no: int) -> tuple[int, list[dict[str, Any]] | Exception]:
        try:
            return page_no, _locate_page(page_images[page_no], page_no)
        except LlmError as e:
            return page_no, e

    located = llm_client.run_concurrent(
        sorted(page_images), _locate_one, concurrency=int(params["concurrency"]))

    with pdf_utils.open_pdf(pdf_path) as doc:
        for page_no, outcome in located:
            if isinstance(outcome, Exception):
                skipped.append({"name": f"{doc_id}-#{page_no}", "reason": str(outcome),
                                "code": "model_call_failed"})
                continue
            blocks, chapter = _page_text_blocks(doc, page_no)
            for j, f in enumerate(outcome, start=1):
                bbox = _valid_bbox(f.get("bbox"))
                if bbox is None:
                    skipped.append({"name": f"{doc_id}-#{page_no}-f{j}",
                                    "reason": f"坐标校验失败：{f.get('bbox')}", "code": "bbox_invalid"})
                    continue
                instance_id = f"{doc_id}-p{page_no}-f{j:02d}"
                crop_rel = f"{CROPS_DIR}/{doc_id}/{instance_id}.png"
                try:
                    px = _crop(page_images[page_no], bbox, output_dir / crop_rel)
                except ValueError as e:
                    skipped.append({"name": instance_id, "reason": str(e), "code": "crop_failed"})
                    continue
                instances.append({
                    "instanceId": instance_id,
                    "pageNo": page_no,
                    "bbox": bbox,
                    "bboxPixel": list(px),
                    "hasNumber": bool(f.get("hasNumber")),
                    "locateConfidence": llm_client.clamp_confidence(f.get("confidence")),
                    "crop": crop_rel,
                    "chapterTitle": chapter,
                    "contextText": _context_for(blocks, bbox, int(params["max_context_chars"])),
                })
    return {
        "docId": doc_id, "fileName": pdf_path.name, "pageCount": page_count,
        "checksum": pdf_utils.sha256_of(pdf_path),
        "instances": instances, "instanceCount": len(instances),
        "skipped": skipped,
    }


def run(input_dir: Path, output_dir: Path, params: dict[str, Any], log) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in input_dir.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf")

    records: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    failed: list[dict[str, str]] = []
    lineage: list[dict[str, Any]] = []

    for path in files:
        base = {"sample_id": path.stem, "source_file": path.name}
        try:
            record = _process_doc(path, output_dir, params, log)
        except PdfError as e:
            msg = str(e)
            code = review_codes.pick(
                ("加密" in msg, "pdf_encrypted"),
                ("页数为 0" in msg, "pdf_empty"),
                ("损坏" in msg, "pdf_corrupt"),
                default="pdf_open_failed")
            failed.append({"name": path.name, "reason": msg, "code": code})
            lineage.append({**base, "action": "fail", "reason": msg})
            continue
        skipped.extend(record.pop("skipped"))
        if record["instanceCount"] == 0:
            failed.append({"name": path.name, "reason": "整份 0 个公式（未定位到公式）", "code": "no_formula"})
            lineage.append({**base, "action": "fail", "reason": "整份 0 个公式"})
            continue
        records.append(record)
        lineage.append({**base, "action": "keep", "metrics": {"instances": record["instanceCount"]}})

    with (output_dir / RECORDS_FILE).open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    total_instances = sum(r["instanceCount"] for r in records)
    log("定位完成：%d 份文档 %d 个公式实例，%d 份失败，%d 条跳过",
        len(records), total_instances, len(failed), len(skipped))
    return {
        "records_file": RECORDS_FILE,
        "summary": {
            "total": len(files), "located": len(records), "failed": len(failed),
            "instances": total_instances, "skipped": len(skipped),
        },
        "skipped": skipped,
        "failed": failed,
        "sample_lineage": lineage,
    }
