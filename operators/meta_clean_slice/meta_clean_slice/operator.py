"""正文抽取与切片 · 算子核心（文本元信息 环节①，纯规则不调模型）。

流程：HTML 解码抽取 → 正文校验（空白页/导航页/无有效段落）→ 按章节→段落切片
（单片 ≤2000 字、重叠 200 字、超长段落硬切）。新闻体裁判定由下游 meta_genre_judge 承担。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .configs import config
from .utils.html_text import extract

OPERATOR_NAME = "正文抽取与切片"
ALLOWED_SUFFIXES = (".html", ".htm", ".zip")

_SOURCE_RE = re.compile(r"来源[：:]\s*([^\s　，,。]+)")

PARAM_DEFAULTS: dict[str, Any] = {
    "slice_max_chars": config.SLICE_MAX_CHARS,
    "slice_overlap_chars": config.SLICE_OVERLAP_CHARS,
    "min_readable_chars": config.MIN_READABLE_CHARS,
    "min_paragraph_chars": config.MIN_PARAGRAPH_CHARS,
    "nav_link_ratio": config.NAV_LINK_RATIO,
}

RECORDS_FILE = "records.jsonl"


def validate_params(params: dict[str, Any]) -> dict[str, Any]:
    merged = {**PARAM_DEFAULTS, **(params or {})}
    if not (100 <= int(merged["slice_max_chars"]) <= 10000):
        raise ValueError("slice_max_chars 须在 100–10000 之间")
    if not (0 <= int(merged["slice_overlap_chars"]) < int(merged["slice_max_chars"])):
        raise ValueError("slice_overlap_chars 须 ≥0 且小于 slice_max_chars")
    return merged


def _check_doc(doc) -> str | None:
    """正文校验：返回跳过原因，通过返回 None。顺序：空白页 → 导航页 → 无有效段落。"""

    if doc.total_chars == 0:
        return "空白页"
    if doc.link_ratio > config.NAV_LINK_RATIO:
        return "导航页"
    if not any(len(p) >= config.MIN_PARAGRAPH_CHARS for p in doc.paragraphs):
        return "无有效段落"
    return None


def _skip_code(reason: str) -> str:
    """跳过原因 → 机器可读码（与 _check_doc 返回文案一一对应）。"""

    return {
        "空白页": "blank_page",
        "导航页": "nav_page",
        "无有效段落": "no_valid_paragraph",
    }.get(reason, "invalid_content")


def _slice_paragraphs(paragraphs: list[str], heading_flags: list[bool], doc_id: str,
                      max_chars: int, overlap: int) -> list[dict[str, Any]]:
    """章节→段落贪心装片；超长段落硬切；新片带上一片末尾 overlap 字。"""

    blocks: list[tuple[str, bool]] = []
    for text, is_heading in zip(paragraphs, heading_flags):
        if len(text) <= max_chars:
            blocks.append((text, is_heading))
        else:  # 超长段落硬切
            step = max_chars - overlap
            for start in range(0, len(text), step):
                blocks.append((text[start:start + max_chars], is_heading))

    slices: list[str] = []
    current: list[str] = []
    current_len = 0
    for text, is_heading in blocks:
        would_exceed = current and current_len + len(text) > max_chars
        chapter_break = (
            is_heading and current and current_len >= config.CHAPTER_BREAK_MIN_CHARS
        )
        if would_exceed or chapter_break:
            slices.append("".join(current))
            tail = "".join(current)[-overlap:] if overlap else ""
            current = [tail] if tail else []
            current_len = len(tail)
        current.append(text)
        current_len += len(text)
    if current and "".join(current).strip():
        slices.append("".join(current))

    return [
        {"sliceId": f"{doc_id}-s{i:02d}", "index": i, "text": s, "charCount": len(s)}
        for i, s in enumerate(slices, start=1)
    ]


def run(input_dir: Path, output_dir: Path, params: dict[str, Any], log) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in input_dir.rglob("*")
                   if p.is_file() and p.suffix.lower() in (".html", ".htm"))
    records: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    lineage: list[dict[str, Any]] = []

    for path in files:
        doc_id = path.stem
        base = {"sample_id": doc_id, "source_file": path.name}
        try:
            doc = extract(path.read_bytes())
        except ValueError as e:
            skipped.append({"name": path.name, "reason": str(e), "code": "html_decode_failed"})
            lineage.append({**base, "action": "skip", "reason": str(e)})
            continue
        reason = _check_doc(doc)
        if reason:
            skipped.append({"name": path.name, "reason": reason, "code": _skip_code(reason)})
            lineage.append({**base, "action": "skip", "reason": reason})
            continue
        slices = _slice_paragraphs(
            doc.paragraphs, doc.heading_flags, doc_id,
            int(params["slice_max_chars"]), int(params["slice_overlap_chars"]))
        # 来源线索：前两段内的「来源：xxx」（供下游体裁判定使用）
        source = None
        for para in doc.paragraphs[:2]:
            m = _SOURCE_RE.search(para)
            if m:
                source = m.group(1)
                break
        records.append({
            "docId": doc_id,
            "fileName": path.name,
            "title": doc.title,
            "source": source,
            "textLength": doc.total_chars,
            "sliceCount": len(slices),
            "slices": slices,
        })
        lineage.append({**base, "action": "keep", "metrics": {"slices": len(slices)}})

    out_file = output_dir / RECORDS_FILE
    with out_file.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    log("清洗完成：%d 篇通过，%d 篇跳过", len(records), len(skipped))
    return {
        "records_file": RECORDS_FILE,
        "summary": {"total": len(files), "kept": len(records), "skipped": len(skipped)},
        "skipped": skipped,
        "failed": [],
        "sample_lineage": lineage,
    }
