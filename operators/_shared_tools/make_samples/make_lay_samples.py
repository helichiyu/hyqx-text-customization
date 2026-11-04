"""复杂版面线小样本：3 页 PDF（双栏版面 / 单栏含表格 / 空白页）+ 1 份加密 PDF。"""

from __future__ import annotations

import argparse
from pathlib import Path

import pymupdf

FONT = "china-s"  # pymupdf 内置 CJK 字体
PW, PH = 595, 842  # A4 点数


def _text(page, x, y, s, size=10):
    page.insert_text((x, y), s, fontname=FONT, fontsize=size)


def _rule_lines(page, x0, y0, x1, n, gap=14):
    for i in range(n):
        y = y0 + i * gap
        page.draw_line((x0, y), (x1, y), color=(0, 0, 0), width=0.6)


def make_layout_pdf(path: Path) -> None:
    doc = pymupdf.open()

    # 第 1 页：双栏版面（页眉/通栏标题/左栏正文/右栏图/右栏正文/页脚）
    p = doc.new_page(width=PW, height=PH)
    _text(p, 40, 30, "某学报 2026年第3期", 8)                      # header
    _text(p, 40, 80, "基于深度学习的复杂版面分析方法研究", 16)        # heading 通栏
    p.draw_rect(pymupdf.Rect(40, 110, 285, 640))                    # 左栏 body
    _rule_lines(p, 50, 125, 275, 35)
    p.draw_rect(pymupdf.Rect(310, 110, 555, 330))                   # 右栏 figure
    p.draw_circle(pymupdf.Point(430, 210), 60, color=(0, 0, 1), width=1.5)
    _text(p, 400, 320, "图1 系统框架图", 9)
    p.draw_rect(pymupdf.Rect(310, 350, 555, 640))                   # 右栏 body
    _rule_lines(p, 320, 365, 545, 18)
    _text(p, 280, 810, "- 12 -", 8)                                 # footer

    # 第 2 页：单栏，含三线表与一行公式
    p = doc.new_page(width=PW, height=PH)
    _text(p, 40, 60, "实验结果", 14)
    _rule_lines(p, 40, 80, 555, 8)
    # 三线表
    top, bot = 250, 400
    p.draw_line((80, top), (515, top), width=1.2)
    p.draw_line((80, top + 22), (515, top + 22), width=0.8)
    p.draw_line((80, bot), (515, bot), width=1.2)
    for i, h in enumerate(["方法", "准确率", "召回率"]):
        _text(p, 110 + i * 150, top + 16, h, 10)
    for r in range(3):
        y = top + 45 + r * 22
        _text(p, 110, y, f"方法{chr(65 + r)}", 10)
        _text(p, 260, y, f"0.9{r}", 10)
        _text(p, 410, y, f"0.8{r}", 10)
    _text(p, 40, 460, "表1 不同方法的性能对比", 9)
    # 独立成行公式（文本模拟）
    _text(p, 180, 540, "F1 = 2 * P * R / (P + R)    (3-1)", 12)
    _rule_lines(p, 40, 580, 555, 10)
    _text(p, 280, 810, "- 13 -", 8)

    # 第 3 页：空白页
    doc.new_page(width=PW, height=PH)

    doc.save(path)
    doc.close()


def make_encrypted_pdf(path: Path) -> None:
    doc = pymupdf.open()
    p = doc.new_page(width=PW, height=PH)
    _text(p, 72, 72, "encrypted page")
    doc.save(path, encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="pw", owner_pw="pw")
    doc.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="samples_pool/lay")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    make_layout_pdf(out / "layout_sample.pdf")
    make_encrypted_pdf(out / "encrypted.pdf")
    print("written", out / "layout_sample.pdf")
    print("written", out / "encrypted.pdf")


if __name__ == "__main__":
    main()
