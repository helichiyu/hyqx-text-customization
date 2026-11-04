"""公式文本线小样本：含独立成行公式（带编号）、行内公式、多行对齐公式的 PDF。

公式用 matplotlib mathtext 渲染成 PNG 再嵌入 PDF，保证视觉上是"印刷体公式"。
"""

from __future__ import annotations

import argparse
import io
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pymupdf

FONT = "china-s"
PW, PH = 595, 842


def render_formula_png(latex: str, fontsize: int = 20) -> bytes:
    fig = plt.figure(figsize=(0.1, 0.1))
    text = fig.text(0, 0, f"${latex}$", fontsize=fontsize)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", pad_inches=0.05, transparent=True)
    plt.close(fig)
    return buf.getvalue()


def make_formula_pdf(path: Path) -> None:
    doc = pymupdf.open()
    p = doc.new_page(width=PW, height=PH)

    _ = p.insert_text((40, 50), "第二章 极限", fontname=FONT, fontsize=16)
    p.insert_text((40, 90), "本节讨论分式与根式的基本运算。设有如下关系：", fontname=FONT, fontsize=11)

    # 独立成行公式（无编号）
    img = render_formula_png(r"\frac{a}{b} + \sqrt{x} = \sum_{i=1}^{n} c_i")
    p.insert_image(pymupdf.Rect(120, 110, 420, 170), stream=img)

    p.insert_text((40, 200), "其中 a、b 为已知常数，x 为自变量，c_i 为第 i 项系数。", fontname=FONT, fontsize=11)
    p.insert_text((40, 230), "行内公式 y=kx+b 不在处理范围内，仅作排版演示。", fontname=FONT, fontsize=11)

    # 带编号的独立公式
    img2 = render_formula_png(r"E = m c^{2}")
    p.insert_image(pymupdf.Rect(160, 260, 360, 320), stream=img2)
    p.insert_text((480, 300), "(2-3)", fontname=FONT, fontsize=11)

    # 多行公式（mathtext 不支持 aligned 环境，用两行独立公式模拟多行排版）
    img3 = render_formula_png(r"f(x) = x^2 + 2x + 1")
    p.insert_image(pymupdf.Rect(120, 350, 420, 400), stream=img3)
    img4 = render_formula_png(r"= (x+1)^2")
    p.insert_image(pymupdf.Rect(120, 405, 360, 450), stream=img4)

    p.insert_text((40, 480), "上述推导在第 2 段给出 a、b 的定义。", fontname=FONT, fontsize=11)

    # 第 2 页：纯文字，无公式（验证"0 个公式"分支不报错）
    p2 = doc.new_page(width=PW, height=PH)
    p2.insert_text((40, 50), "第三章 导数（引言）", fontname=FONT, fontsize=16)
    p2.insert_text((40, 90), "本章引言部分不含任何公式，仅作文字说明。", fontname=FONT, fontsize=11)

    doc.save(path)
    doc.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="samples_pool/fml")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    make_formula_pdf(out / "formula_sample.pdf")
    print("written", out / "formula_sample.pdf")


if __name__ == "__main__":
    main()
