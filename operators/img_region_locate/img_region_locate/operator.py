"""图片区域定位与裁切 · 算子核心（图文融合 环节①，CV/规则，不调模型）。

口径（待确认 Q1 的默认实现）：整图直通 + 拍照件黑边/白边自动裁剪。
流程：逐张打开校验 → 以四角背景色为基准检测均色边框并裁剪 → 登记 ImageRegion
（像素 bbox、处理后图路径）。处理失败重试 2 次（共 3 次），仍失败 → 跳过并记录。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops

from .configs import config

OPERATOR_NAME = "图片区域定位与裁切"
ALLOWED_SUFFIXES = (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff", ".zip")

PARAM_DEFAULTS: dict[str, Any] = {
    "border_tolerance": config.BORDER_TOLERANCE,
    "min_crop_size": config.MIN_CROP_SIZE,
}

RECORDS_FILE = "records.jsonl"
REGIONS_DIR = "regions"


def validate_params(params: dict[str, Any]) -> dict[str, Any]:
    merged = {**PARAM_DEFAULTS, **(params or {})}
    if not (0 <= int(merged["border_tolerance"]) <= 64):
        raise ValueError("border_tolerance 须在 0–64 之间")
    if int(merged["min_crop_size"]) < 8:
        raise ValueError("min_crop_size 须 ≥8")
    return merged


def _detect_border_box(img: Image.Image, tolerance: int) -> tuple[int, int, int, int]:
    """以四角均色为背景基准，返回内容区像素 bbox（无边框时返回整图）。"""

    rgb = img.convert("RGB")
    w, h = rgb.size
    corners = [rgb.getpixel((0, 0)), rgb.getpixel((w - 1, 0)),
               rgb.getpixel((0, h - 1)), rgb.getpixel((w - 1, h - 1))]
    # 四角取均值作背景色
    bg = tuple(sum(c[i] for c in corners) // 4 for i in range(3))
    background = Image.new("RGB", rgb.size, bg)
    diff = ImageChops.difference(rgb, background)
    # 容差：低于阈值的差异视为背景
    mask = diff.convert("L").point(lambda v: 255 if v > tolerance else 0)
    box = mask.getbbox()
    return box if box else (0, 0, w, h)


def _locate_one(src: Path, out_path: Path, tolerance: int, min_size: int) -> dict[str, Any]:
    """单张处理：打开 → 边框检测 → 裁剪保存。抛异常由调用方重试。"""

    with Image.open(src) as img:
        img.load()
        w, h = img.size
        box = _detect_border_box(img, tolerance)
    x1, y1, x2, y2 = box
    if (x2 - x1) < min_size or (y2 - y1) < min_size:
        raise ValueError(f"裁剪后尺寸过小：{x2 - x1}x{y2 - y1}")
    cropped = (x1, y1, x2, y2) != (0, 0, w, h)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as img:
        img.load()
        region_img = img.crop(box) if cropped else img.copy()
        region_img.convert("RGB").save(out_path)
    return {
        "bbox": [x1, y1, x2, y2],
        "cropped": cropped,
        "width": x2 - x1, "height": y2 - y1,
        "sourceWidth": w, "sourceHeight": h,
    }


def run(input_dir: Path, output_dir: Path, params: dict[str, Any], log) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    suffixes = tuple(s for s in ALLOWED_SUFFIXES if s != ".zip")
    files = sorted(p for p in input_dir.rglob("*") if p.is_file() and p.suffix.lower() in suffixes)
    tolerance = int(params["border_tolerance"])
    min_size = int(params["min_crop_size"])

    records: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    lineage: list[dict[str, Any]] = []

    for path in files:
        image_id = path.stem
        base = {"sample_id": image_id, "source_file": path.name}
        out_path = output_dir / REGIONS_DIR / f"{image_id}.png"
        last_err: str | None = None
        region: dict[str, Any] | None = None
        for attempt in range(1, config.MAX_ATTEMPTS + 1):
            try:
                region = _locate_one(path, out_path, tolerance, min_size)
                break
            except Exception as e:
                last_err = f"{type(e).__name__}: {e}"
                log("区域定位第 %d 次失败（%s）：%s", attempt, path.name, last_err)
        if region is None:
            reason = f"区域定位失败（重试 {config.MAX_ATTEMPTS - 1} 次）：{last_err}"
            skipped.append({"name": path.name, "reason": reason, "code": "locate_failed"})
            lineage.append({**base, "action": "skip", "reason": reason})
            continue
        records.append({
            "imageId": image_id, "fileName": path.name,
            "image": str(out_path.relative_to(output_dir)),
            "region": region,
        })
        lineage.append({**base, "action": "keep",
                        "metrics": {"cropped": region["cropped"],
                                    "size": f"{region['width']}x{region['height']}"}})

    with (output_dir / RECORDS_FILE).open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    cropped_count = sum(1 for r in records if r["region"]["cropped"])
    log("区域定位完成：%d 张通过（%d 张裁边），%d 张跳过", len(records), cropped_count, len(skipped))
    return {
        "records_file": RECORDS_FILE,
        "summary": {"total": len(files), "located": len(records),
                    "cropped": cropped_count, "skipped": len(skipped)},
        "skipped": skipped,
        "failed": [],
        "sample_lineage": lineage,
    }
