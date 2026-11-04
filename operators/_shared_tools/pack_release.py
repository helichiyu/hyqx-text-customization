"""打包 release 交付目录：每算子一个 zip（仅 Docker 构建所需内容）+ 编排与对接文件。

用法（项目根执行）：
    python -I operators/_shared_tools/pack_release.py

产物（项目根 release/）：
    <tag>.zip × 11          Dockerfile / requirements.txt / inference.py / map.json / <tag>/（内层实现，剔除 __pycache__）
    docker-compose.yml      11 服务一键编排（端口 6301–6311、共享数据卷）
    chain_example.py        四条产线 HTTP 调用示例
    前后端对接说明.md        分工边界 + 契约 + 调用时序
    docs/                   22 份算子说明书 / 测试指令
"""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

OPERATORS = Path(__file__).resolve().parents[1]
PROJECT = OPERATORS.parent
RELEASE = PROJECT / "release"

TAGS = ["meta_clean_slice", "meta_genre_judge", "meta_fact_extract", "meta_field_fill",
        "lay_page_render", "lay_page_detect", "fml_formula_locate", "fml_formula_recognize",
        "img_region_locate", "img_type_classify", "img_struct_describe"]

ZIP_ROOT_FILES = ["Dockerfile", "requirements.txt", "inference.py", "map.json"]

EXCLUDE_DIR_NAMES = {"__pycache__", ".pytest_cache", ".idea", ".git"}


def add_tree(zf: zipfile.ZipFile, src: Path, arc: Path) -> int:
    n = 0
    for p in sorted(src.rglob("*")):
        if any(part in EXCLUDE_DIR_NAMES for part in p.parts):
            continue
        if p.is_file():
            zf.write(p, arc / p.relative_to(src))
            n += 1
    return n


def main() -> None:
    if RELEASE.exists():
        shutil.rmtree(RELEASE)
    (RELEASE / "docs").mkdir(parents=True)

    for tag in TAGS:
        pkg = OPERATORS / tag
        out = RELEASE / f"{tag}.zip"
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in ZIP_ROOT_FILES:
                zf.write(pkg / f, f)
            n = add_tree(zf, pkg / tag, tag)
        print(f"[zip] {out.name:32s} {out.stat().st_size / 1024:8.1f} KB（内层 {n} 个文件）")

    for f in ["docker-compose.yml", "chain_example.py", "前后端对接说明.md"]:
        shutil.copy2(OPERATORS / f, RELEASE / f)
    for tag in TAGS:
        for f in (OPERATORS / tag).glob(f"{tag}-*.md"):
            shutil.copy2(f, RELEASE / "docs" / f.name)
    (RELEASE / "README.md").write_text(
        "# release · 交付包\n\n"
        "- `<算子目录名>.zip` × 11：Docker 构建所需全部内容（解压到同名目录后 compose 构建）\n"
        "- `docker-compose.yml`：一键起 11 个服务（宿主机端口 6301–6311，共享数据卷 ./op-runtime）\n"
        "- `前后端对接说明.md`：分工边界、三接口契约、产线编排顺序、调用时序与注意事项（**先读这份**）\n"
        "- `chain_example.py`：四条产线完整调用示例（compose 起服务后直接跑）\n"
        "- `docs/`：11 份算子说明书 + 11 份测试指令\n\n"
        "快速开始：\n\n```bash\nfor f in *.zip; do unzip -q \"$f\" -d \"${f%.zip}\"; done\ndocker compose up -d --build\npython chain_example.py meta   # 另有 lay / fml / img [几何|统计|表格|示意]\n```\n",
        encoding="utf-8")
    print(f"[ok] release 就绪：{RELEASE}")


if __name__ == "__main__":
    main()
