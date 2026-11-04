"""算子骨架生成器：按 REGISTRY 生成 11 个算子包的目录骨架。

用法：python gen_inference.py
- 每个算子得到：inference.py（模板原样复制）、map.json、内层包（__init__.py + operator.py 桩）、
  dataset/sample/、tests/；
- operator.py 桩的 run() 返回"尚未实现"，实现见各阶段任务；
- 幂等：已存在的文件不覆盖（加 --force 才覆盖 inference.py）。
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

SHARED = Path(__file__).resolve().parent
OPERATORS_ROOT = SHARED.parent
TEMPLATE = SHARED / "inference_template.py"

#: 11 个算子登记：目录名 → (中文名, 产线)
REGISTRY: dict[str, tuple[str, str]] = {
    "meta_clean_slice": ("正文抽取与切片", "文本元信息"),
    "meta_genre_judge": ("新闻体裁判定", "文本元信息"),
    "meta_fact_extract": ("新闻事实抽取", "文本元信息"),
    "meta_field_fill": ("元信息三组补全", "文本元信息"),
    "lay_page_render": ("版面分页渲染", "复杂版面"),
    "lay_page_detect": ("逐页版面检测", "复杂版面"),
    "fml_formula_locate": ("公式区域定位与裁切", "公式文本"),
    "fml_formula_recognize": ("公式识别与结构化标注", "公式文本"),
    "img_region_locate": ("图片区域定位与裁切", "图文融合"),
    "img_type_classify": ("图片判型", "图文融合"),
    "img_struct_describe": ("图文要素与描述生成", "图文融合"),
}

_OPERATOR_STUB = '''"""{name} · 算子核心（桩，待实现）。

契约见 inference.py 头部注释：run(input_dir, output_dir, params, log) -> dict。
"""

from pathlib import Path
from typing import Any

OPERATOR_NAME = "{name}"
#: 收件白名单（/uploadFile 用）：实现时按需声明 ALLOWED_SUFFIXES = (".html",) 收紧；
#: 不声明则收外壳默认全量白名单。

#: 算子参数默认值与说明（validate_params 据此校验）
PARAM_DEFAULTS: dict[str, Any] = {{}}


def validate_params(params: dict[str, Any]) -> dict[str, Any]:
    merged = {{**PARAM_DEFAULTS, **(params or {{}})}}
    return merged


def run(input_dir: Path, output_dir: Path, params: dict[str, Any], log) -> dict[str, Any]:
    raise NotImplementedError("{tag} 尚未实现")
'''


#: 需要 vendor 进每个算子内层包 utils/ 的共享模块（交付包自包含，不依赖 _shared_tools）
VENDOR_MODULES = ["llm_config.py", "llm_client.py", "pdf_utils.py", "review_codes.py"]


def scaffold(force: bool = False) -> list[str]:
    created: list[str] = []
    for tag, (name, _line) in REGISTRY.items():
        root = OPERATORS_ROOT / tag
        inner = root / tag
        for d in (inner / "configs", inner / "utils", inner / "dataset" / "sample", inner / "tests"):
            d.mkdir(parents=True, exist_ok=True)

        inference = root / "inference.py"
        if force or not inference.exists():
            shutil.copyfile(TEMPLATE, inference)

        (root / "map.json").write_text(
            json.dumps({tag: name}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        (inner / "__init__.py").write_text("", encoding="utf-8")
        (inner / "utils" / "__init__.py").write_text("", encoding="utf-8")
        for mod in VENDOR_MODULES:
            shutil.copyfile(SHARED / mod, inner / "utils" / mod)
        stub = inner / "operator.py"
        if not stub.exists():
            stub.write_text(_OPERATOR_STUB.format(name=name, tag=tag), encoding="utf-8")
        created.append(tag)
    return created


if __name__ == "__main__":
    tags = scaffold(force="--force" in sys.argv)
    print(f"骨架就绪 {len(tags)} 个：")
    for t in tags:
        print(" -", t)
