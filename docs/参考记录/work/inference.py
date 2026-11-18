"""预训练文本算子池入口（联调部署形态，对外端口 17014）。

一个容器承载当前目录下全部算子（启动时自动发现，复制算子目录进来即扩充），
POST /predict?detection=PTt_xxx 按标识路由
（规范 2.3 池化形态；与单算子服务共用同一条处理管线，后端无感知）。

本地开发：python inference.py --port 17014
生产部署：gunicorn -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:17014 inference:app
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from common.server import create_pool_app  # noqa: E402

# 主表序号顺序（用于排序；本 work 目录为联调子集，只含部分算子目录，
# 其余在原仓库，复制进来后自动被发现并注册，无需改本文件）
POOL_ORDER = [
    "PTt_filter_anomalous_file",
    "PTt_extract_html_body",
    "PTt_extract_xml_body",
    "PTt_extract_pdf_body",
    "PTt_extract_docx_body",
    "PTt_extract_doc_body",
    "PTt_extract_paper_body",
    "PTt_remove_layout_noise",
    "PTt_normalize_utf8_encoding",
    "PTt_fix_mojibake",
    "PTt_exact_hash_dedup",
    "PTt_clean_web_noise",
    "PTt_filter_length_anomaly",
    "PTt_filter_erroneous_text",
    "PTt_filter_semantic_anomaly",
    "PTt_filter_sensitive_content",
    "PTt_redact_pii",
    "PTt_chinese_tokenize",
    "PTt_clean_ner_en",
    "PTt_normalize_format",
    "PTt_semantic_chunking",
    "PTt_sliding_window_chunking",
    "PTt_approx_dedup_large",
    "PTt_build_qa_pairs",
    "PTt_convert_mlm_format",
    "PTt_build_nsp_pairs",
    "PTt_check_vocab_coverage",
    "PTt_check_domain_relevance",
    "PTt_check_length_distribution",
    "PTt_check_topic_distribution",
    "PTt_measure_error_rate",
    "PTt_generate_tokens",
]


def discover_pool_operators() -> list:
    """发现当前目录下实际存在的算子（PTt_*/model/network.py）。

    排序：先按 POOL_ORDER 主表顺序，清单外新算子按字典序追加。
    """
    present = sorted(
        item.name for item in HERE.iterdir()
        if item.is_dir() and item.name.startswith("PTt_")
        and (item / "model" / "network.py").exists()
    )
    ordered = [name for name in POOL_ORDER if name in present]
    ordered += [name for name in present if name not in POOL_ORDER]
    return ordered


POOL_OPERATORS = discover_pool_operators()


def build_registry() -> dict:
    from common.operator_base import Operator

    registry = {}
    for detection in POOL_OPERATORS:
        op_dir = HERE / detection
        network = op_dir / "model" / "network.py"
        if not network.exists():
            print(f"[WARN] 池注册跳过（缺实现）: {detection}")
            continue
        spec = importlib.util.spec_from_file_location(f"pool_op_{detection}", str(network))
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        # 算子内可能存在包内绝对导入（如 #17 的 from model.bert_adapter import ...）：
        # 加载期间临时把算子目录挂到 sys.path 首位，加载完清理 model 包缓存，
        # 避免 32 个同名 model 包互相污染
        sys.path.insert(0, str(op_dir))
        polluted = [name for name in sys.modules if name == "model" or name.startswith("model.")]
        try:
            spec.loader.exec_module(module)
        finally:
            sys.path.remove(str(op_dir))
            for name in polluted:
                sys.modules.pop(name, None)
        cls = getattr(module, "OPERATOR_CLASS", None)
        if cls is None:
            # 兜底：取模块内定义的首个 Operator 具体子类（无 OPERATOR_CLASS 别名时）
            candidates = [
                obj for obj in vars(module).values()
                if isinstance(obj, type) and issubclass(obj, Operator)
                and obj is not Operator and obj.__module__ == module.__name__
            ]
            cls = candidates[0] if candidates else None
        if cls is None:
            print(f"[WARN] 池注册跳过（无算子类）: {detection}")
            continue
        operator = cls()
        registry[operator.detection] = operator
        print(f"[POOL] {operator.detection}（{operator.name}）")
    return registry


REGISTRY = build_registry()
app = create_pool_app(REGISTRY)


if __name__ == "__main__":
    # 开发入口必须直接跑池 app（gunicorn 生产入口同为 inference:app）。
    # 注意：不能用 run_service——它按"单算子"建 create_app，会把池上所有
    # detection 都判成不匹配。
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser(description="预训练文本算子池（开发模式）")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", "-p", type=int, default=17014)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)
