"""图文融合线小样本：几何图 / 统计图 / 表格图 / 示意图 各 1 张 + 1 张低分辨率图（测准入剔除）。"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont

from _fonts import find_cjk_font, setup_matplotlib_cjk

FONT_PATH = find_cjk_font()


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_PATH, size)


def make_geometry(path: Path) -> None:
    """平面几何图：半圆（直径 AB，圆心 O），弧上点 C，连线 CO。"""
    img = Image.new("RGB", (1000, 800), "white")
    d = ImageDraw.Draw(img)
    f = _font(36)
    d.arc([200, 200, 800, 800], start=180, end=360, fill="black", width=4)
    d.line([(200, 500), (800, 500)], fill="black", width=4)
    d.ellipse([490, 490, 510, 510], fill="black")
    # C 在弧上 135° 处
    cx, cy, r = 500, 500, 300
    import math
    px = cx + r * math.cos(math.radians(135))
    py = cy - r * math.sin(math.radians(135))
    d.line([(px, py), (cx, cy)], fill="black", width=3)
    d.text((170, 510), "A", font=f, fill="black")
    d.text((800, 510), "B", font=f, fill="black")
    d.text((505, 510), "O", font=f, fill="black")
    d.text((px - 60, py - 10), "C", font=f, fill="black")
    img.save(path)


def make_chart(path: Path) -> None:
    """统计图：折线图，2021-2024 年产值。"""
    setup_matplotlib_cjk()
    fig, ax = plt.subplots(figsize=(8, 6), dpi=150)
    years = ["2021", "2022", "2023", "2024"]
    values = [120, 150, 135, 180]
    ax.plot(years, values, marker="o", label="产值")
    ax.set_title("2021-2024 年产值变化")
    ax.set_xlabel("年份")
    ax.set_ylabel("产值（亿元）")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.savefig(path)
    plt.close(fig)


def make_table(path: Path) -> None:
    """普通表格图：3 列 4 行带全框线。"""
    img = Image.new("RGB", (1000, 700), "white")
    d = ImageDraw.Draw(img)
    f = _font(32)
    d.text((300, 40), "成绩统计表", font=_font(40), fill="black")
    x0, y0, cw, rh = 100, 120, 260, 90
    rows = [["姓名", "语文", "数学"], ["张三", "92", "88"], ["李四", "85", "95"], ["王五", "90", "91"]]
    for r, row in enumerate(rows):
        for c, cell in enumerate(row):
            d.rectangle([x0 + c * cw, y0 + r * rh, x0 + (c + 1) * cw, y0 + (r + 1) * rh], outline="black", width=3)
            d.text((x0 + c * cw + 60, y0 + r * rh + 25), cell, font=f, fill="black")
    img.save(path)


def make_schematic(path: Path) -> None:
    """示意图：采集 → 清洗 → 标注 流程。"""
    img = Image.new("RGB", (1000, 700), "white")
    d = ImageDraw.Draw(img)
    f = _font(36)
    boxes = [(80, 300, 280, 420, "采集"), (400, 300, 600, 420, "清洗"), (720, 300, 920, 420, "标注")]
    for x0, y0, x1, y1, label in boxes:
        d.rectangle([x0, y0, x1, y1], outline="black", width=4)
        d.text((x0 + 55, y0 + 40), label, font=f, fill="black")
    for x0, x1 in ((280, 400), (600, 720)):
        d.line([(x0, 360), (x1, 360)], fill="black", width=4)
        d.polygon([(x1 - 20, 350), (x1, 360), (x1 - 20, 370)], fill="black")
    d.text((330, 60), "数据处理流程示意图", font=_font(44), fill="black")
    img.save(path)


def make_lowres(path: Path) -> None:
    """低分辨率图（< 600x600）：测准入剔除分支。"""
    img = Image.new("RGB", (320, 240), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([40, 40, 280, 200], outline="black", width=2)
    img.save(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="samples_pool/img")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, fn in [
        ("geometry_001.jpg", make_geometry),
        ("chart_001.jpg", make_chart),
        ("table_001.jpg", make_table),
        ("schematic_001.jpg", make_schematic),
        ("lowres_001.jpg", make_lowres),
    ]:
        fn(out / name)
        print("written", out / name)


if __name__ == "__main__":
    main()
