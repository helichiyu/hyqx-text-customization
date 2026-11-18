"""全链路贯通自查：按 Excel 环节顺序 #2→…→#37 串行跑真实语料。

用法：python tools/chain_check.py [文档数，默认 8]

文本流转约定：以 {fieldName: text} 字典为链路载体——
- 文本型算子输出 text 字段则更新，否则沿用入参文本（如 #12/#17 只出指标）
- action=remove 的记录退出链路；review（质检/疑似重复）按去向说明处理
- 空输入的环节自动跳过并标注（不误报）
- 每步校验契约不变量：无异常、结果数=输入数、action 合法；
  LLM 算子校验引擎名（走 API 且未降级）
"""

from __future__ import annotations

import importlib.util
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from common.operator_base import OperatorContext, TextRecord  # noqa: E402


def load(op_dir: str):
    op_path = str(ROOT / op_dir)
    sys.path.insert(0, op_path)
    spec = importlib.util.spec_from_file_location(
        f"chain_{op_dir}", str(ROOT / op_dir / "model" / "network.py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(op_path)
        for key in [k for k in sys.modules if k == "model" or k.startswith("model.")]:
            sys.modules.pop(key, None)
    return module.OPERATOR_CLASS()


VALID_ACTIONS = {"keep", "remove", "review"}
failures = []


def check_step(name: str, out, n_in: int):
    problems = []
    if len(out.results) != n_in:
        problems.append(f"结果数 {len(out.results)} != 输入数 {n_in}")
    for r in out.results:
        if r.action not in VALID_ACTIONS:
            problems.append(f"非法 action: {r.action}")
    if problems:
        failures.append(f"{name}: " + "; ".join(problems[:3]))
    return not problems


def run_step(name, op_dir, texts: dict, params=None, resources=None,
             engine_expect=None, keep_review=False):
    """通用文本环节。返回过滤后的 {name: text}。"""
    if not texts:
        print(f"{name}: 输入为空，跳过")
        return texts
    op = load(op_dir)
    records = [TextRecord(n, t) for n, t in texts.items()]
    out = op.process(records, params=params, resources=resources)
    ok = check_step(name, out, len(texts))
    kept = {}
    removed = review = 0
    for r in out.results:
        if engine_expect and engine_expect not in r.fields.get("engine", engine_expect):
            failures.append(f"{name}: 引擎异常 {r.fields.get('engine', '(无)')}")
        if r.action == "remove":
            removed += 1
        elif r.action == "review" and not keep_review:
            review += 1
        else:
            kept[r.fieldName] = r.fields.get("text") or texts[r.fieldName]
    info = ""
    if out.results and "engine" in out.results[0].fields:
        info = f" [引擎={out.results[0].fields['engine']}]"
    print(f"{name}: {len(texts)}→{len(kept)}"
          + (f"（remove {removed} review {review}）" if removed or review else "") + info)
    return kept


def main(n_docs: int = 8):
    print(f"=== 全链路贯通自查（{n_docs} 篇真实网页） ===")
    pages = sorted((ROOT / "tests_assets" / "real_pages").glob("*.html"))[:n_docs]
    print(f"输入: {len(pages)} 篇")

    # ---- 文件级：#2 → #3 ----
    op2 = load("PTt_filter_anomalous_file")
    passed = []
    for p in pages:
        raw = p.read_bytes()
        out = op2.process([TextRecord(p.stem, raw.decode("utf-8", "replace"))],
                          context=OperatorContext(raw=raw, filename=p.name))
        check_step("#2 异常过滤", out, 1)
        if out.results[0].action == "keep":
            passed.append(p)
    print(f"#2 异常过滤: {len(pages)}→{len(passed)}")

    op3 = load("PTt_extract_html_body")
    texts = {}
    for p in passed:
        raw = p.read_bytes()
        out = op3.process([TextRecord(p.stem, raw.decode("utf-8", "replace"))],
                          context=OperatorContext(raw=raw, filename=p.name))
        check_step("#3 HTML提取", out, 1)
        if out.results[0].action == "keep":
            texts[p.stem] = out.results[0].fields.get("text", "")
    print(f"#3 HTML提取: {len(passed)}→{len(texts)}")

    # ---- 清洗·正文/格式/过滤 ----
    texts = run_step("#9 清除版式噪声", "PTt_remove_layout_noise", texts)
    texts = run_step("#13 网页噪声清理", "PTt_clean_web_noise", texts)
    texts = run_step("#10 UTF-8归一化", "PTt_normalize_utf8_encoding", texts)
    texts = run_step("#11 乱码检测替换", "PTt_fix_mojibake", texts)
    texts = run_step("#12 精确哈希去重", "PTt_exact_hash_dedup", texts)
    texts = run_step("#14 长度过滤", "PTt_filter_length_anomaly", texts)
    texts = run_step("#15 错误文本过滤(API)", "PTt_filter_erroneous_text", texts, engine_expect="glm")
    texts = run_step("#16 语义异常过滤(API)", "PTt_filter_semantic_anomaly", texts, engine_expect="glm")
    texts = run_step("#17 敏感检测(本地BERT)", "PTt_filter_sensitive_content", texts)
    texts = run_step("#18 PII脱敏", "PTt_redact_pii", texts)

    # ---- 加工·分片 ----
    texts = run_step("#19 中文分词", "PTt_chinese_tokenize", texts)
    texts = run_step("#20 英文NER", "PTt_clean_ner_en", texts)
    texts = run_step("#21 格式规范化", "PTt_normalize_format", texts)

    if texts:
        op22 = load("PTt_semantic_chunking")
        out = op22.process([TextRecord(n, t) for n, t in texts.items()],
                           params={"最小分块长度": "30"})
        check_step("#22 语义分块", out, len(texts))
        chunks = {}
        for r in out.results:
            for i, piece in enumerate(r.fields.get("texts", [])):
                if piece.strip():
                    chunks[f"{r.fieldName}#c{i}"] = piece
        print(f"#22 语义分块: {len(texts)} 篇 → {len(chunks)} 块")
    else:
        chunks = {}
        print("#22 语义分块: 输入为空，跳过")

    chunks = run_step("#24 近似去重(打标)", "PTt_approx_dedup_large", chunks, keep_review=True)

    # ---- 样本构建（QA 对新闻语料 review 属预期；MLM/NSP 抽 4 块） ----
    if chunks:
        op25 = load("PTt_build_qa_pairs")
        out = op25.process([TextRecord(n, t) for n, t in chunks.items()])
        check_step("#25 QA样本构建", out, len(chunks))
        qa_ok = sum(1 for r in out.results if r.action == "keep")
        print(f"#25 QA样本构建: 成功 {qa_ok}/{len(chunks)}（新闻语料无 question/answer 字段，review 属预期）")

        sample = dict(list(chunks.items())[:4])
        op26 = load("PTt_convert_mlm_format")
        out = op26.process([TextRecord(n, t) for n, t in sample.items()])
        check_step("#26 MLM格式转换", out, len(sample))
        print(f"#26 MLM格式转换: {sum(1 for r in out.results if r.fields.get('samples'))}/{len(sample)} 产出掩码样本")

        op27 = load("PTt_build_nsp_pairs")
        out = op27.process([TextRecord(n, t) for n, t in sample.items()])
        check_step("#27 NSP拼接", out, len(sample))
        print(f"#27 NSP拼接: {sum(len(r.fields.get('samples', [])) for r in out.results)} 个句对")

        # ---- 质量评估 ----
        op28 = load("PTt_check_vocab_coverage")
        out = op28.process([TextRecord(n, t) for n, t in chunks.items()])
        check_step("#28 词汇覆盖率", out, len(chunks))
        print(f"#28 词汇覆盖率: rate={out.extras.get('rate')}（小样本 vs 内置词典，review 属预期）")

        texts29 = run_step("#29 领域相关性", "PTt_check_domain_relevance", chunks,
                           params={"领域关键词列表": "数据；模型；算法；平台；技术"})

        op30 = load("PTt_check_length_distribution")
        out = op30.process([TextRecord(n, t) for n, t in chunks.items()])
        check_step("#30 长度分布", out, len(chunks))
        stats = out.extras.get("lengthStats") or {}
        print(f"#30 长度分布: p50={stats.get('p50')} p90={stats.get('p90')} 达标率={stats.get('inRangeRatio')}")

        op31 = load("PTt_check_topic_distribution")
        out = op31.process([TextRecord(n, t) for n, t in chunks.items()])
        check_step("#31 主题打标", out, len(chunks))
        dist = out.extras.get("distribution") or {}
        top = max(dist, key=lambda k: dist[k]["share"]) if dist else "-"
        print(f"#31 主题打标: 最大主线={top}")

        op32 = load("PTt_measure_error_rate")
        out = op32.process([TextRecord(n, t) for n, t in list(chunks.items())[:3]],
                           params={"抽检样本数": "3"})
        check_step("#32 错误率检测(API)", out, 3)
        eng32 = out.results[0].fields.get("engine", "-") if out.results else "-"
        print(f"#32 错误率检测: avgErrorRate={out.extras.get('avgErrorRate')} [引擎={eng32}]")
        if "glm" not in eng32:
            failures.append(f"#32 引擎异常: {eng32}")

        # ---- 交付 ----
        final = list((texts29 or chunks).items())[:4]
        op37 = load("PTt_generate_tokens")
        out = op37.process([TextRecord(n, t) for n, t in final])
        check_step("#37 Token序列", out, len(final))
        sha = (out.extras.get("tokenizer") or {}).get("vocabSha256", "")[:12]
        print(f"#37 Token序列: {sum(1 for r in out.results if r.fields.get('tokens'))}/{len(final)} 产出 [vocabSha={sha}…]")
    else:
        print("#25~#37: 输入为空，跳过")

    print()
    if failures:
        print(f"=== ✗ 链路发现问题 {len(failures)} 处 ===")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print("=== ✓ 全链路贯通通过（#2→#3→#9→#13→#10→#11→#12→#14→#15(API)→#16(API)→#17(BERT)→#18→#19→#20→#21→#22→#24→#25→#26→#27→#28→#29→#30→#31→#32(API)→#37）===")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8)
