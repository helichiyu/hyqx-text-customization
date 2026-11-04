"""样本生成共享工具：Windows 中文字体解析。"""

from __future__ import annotations

from pathlib import Path

_FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyh.ttc",    # 微软雅黑
    "C:/Windows/Fonts/simsun.ttc",  # 宋体
    "C:/Windows/Fonts/simhei.ttf",  # 黑体
]


def find_cjk_font() -> str:
    for p in _FONT_CANDIDATES:
        if Path(p).exists():
            return p
    raise RuntimeError("找不到中文字体（微软雅黑/宋体/黑体）")


def setup_matplotlib_cjk() -> None:
    import matplotlib

    matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun"]
    matplotlib.rcParams["axes.unicode_minus"] = False
