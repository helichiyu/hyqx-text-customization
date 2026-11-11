"""打包单容器 Docker 部署包：11 个算子合并为 op-custom-text（端口 17022）。

用法（项目根执行）：
    python -I operators/_shared_tools/pack_docker_bundle.py

产物：
    release/op-custom-text-docker/
        docker-compose.yml
        op-custom-text/            # Docker 构建上下文
            Dockerfile / requirements.txt / nginx.conf / supervisor.py / .dockerignore
            ops/<tag>/             # 每个算子仅保留运行所需文件
    release/op-custom-text-docker.zip

每个算子只复制 Docker 构建必需内容：
    inference.py / map.json / <tag>/（剔除 tests、dataset、README.md、__pycache__）
"""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

OPERATORS = Path(__file__).resolve().parents[1]
PROJECT = OPERATORS.parent
RELEASE_ROOT = PROJECT / "release"
BUNDLE = RELEASE_ROOT / "op-custom-text-docker"
CONTEXT = BUNDLE / "op-custom-text"
DEPLOY_TEMPLATE = OPERATORS / "_deploy"

TAGS = ["meta_clean_slice", "meta_genre_judge", "meta_fact_extract", "meta_field_fill",
        "lay_page_render", "lay_page_detect", "fml_formula_locate", "fml_formula_recognize",
        "img_region_locate", "img_type_classify", "img_struct_describe"]

ROOT_FILES = ["inference.py", "map.json"]
EXCLUDE_DIR_NAMES = {"__pycache__", ".pytest_cache", ".idea", ".git"}
EXCLUDE_PKG_DIRS = {"tests", "dataset"}
EXCLUDE_FILE_NAMES = {"README.md"}


def copy_operator(tag: str) -> int:
    src = OPERATORS / tag
    dst = CONTEXT / "ops" / tag
    dst.mkdir(parents=True)
    count = 0

    for name in ROOT_FILES:
        shutil.copy2(src / name, dst / name)
        count += 1

    pkg_src = src / tag
    pkg_dst = dst / tag
    for path in sorted(pkg_src.rglob("*")):
        rel = path.relative_to(pkg_src)
        if any(part in EXCLUDE_DIR_NAMES for part in path.parts):
            continue
        if rel.parts and rel.parts[0] in EXCLUDE_PKG_DIRS:
            continue
        if path.name in EXCLUDE_FILE_NAMES:
            continue
        target = pkg_dst / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif path.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            count += 1
    return count


def zip_bundle() -> Path:
    archive = RELEASE_ROOT / "op-custom-text-docker.zip"
    archive.unlink(missing_ok=True)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(BUNDLE.rglob("*")):
            if any(part in EXCLUDE_DIR_NAMES for part in path.parts):
                continue
            if path.is_file() and path.suffix != ".pyc":
                zf.write(path, Path(BUNDLE.name) / path.relative_to(BUNDLE))
    return archive


def reset_bundle_dir() -> None:
    """清空交付目录内容但保留根目录本身（Windows 下根目录可能被资源管理器/构建进程占用）。"""
    BUNDLE.mkdir(parents=True, exist_ok=True)
    for child in BUNDLE.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def main() -> None:
    reset_bundle_dir()
    CONTEXT.mkdir(parents=True)
    (CONTEXT / "ops").mkdir()

    for name in ["Dockerfile", "requirements.txt", "nginx.conf", "supervisor.py", ".dockerignore"]:
        shutil.copy2(DEPLOY_TEMPLATE / "op-custom-text" / name, CONTEXT / name)
    shutil.copy2(OPERATORS / "docker-compose.yml", BUNDLE / "docker-compose.yml")

    total = 0
    for tag in TAGS:
        n = copy_operator(tag)
        total += n
        print(f"[ops] {tag:24s} {n:4d} files")

    archive = zip_bundle()
    print(f"[ok] {BUNDLE}（{total} 个文件）")
    print(f"[zip] {archive}（{archive.stat().st_size / 1024 / 1024:.1f} MB）")


if __name__ == "__main__":
    main()
