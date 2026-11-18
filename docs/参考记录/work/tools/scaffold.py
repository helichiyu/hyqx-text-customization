"""算子脚手架：按元数据表生成算子目录骨架（inference/config/map/Dockerfile 等）。

用法：python tools/scaffold.py PTt_extract_xml_body ...（不传参数则生成元数据表全部算子）
核心逻辑 model/network.py 与 tests/test_network.py 需手写覆盖（本工具只生成占位）。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BASE_REQUIREMENTS = [
    "fastapi>=0.100.0",
    "uvicorn>=0.23.0",
    "gunicorn>=21.2.0",
    "python-multipart>=0.0.6",
    "orjson>=3.19.0",
    "PyYAML>=6.0",
]

# 算子元数据表：params = Excel 配置项中的算子侧参数（规范 5.3），output_fields = 业务字段（规范 4.4）
OPERATORS = {
    "PTt_exact_hash_dedup": {
        "seq": 12, "name": "全文精确哈希去重", "type": "算法", "stage": "清洗·过滤", "port": 6312,
        "skippable": "否（必须）",
        "params": {"Hash算法": "MD5"},
        "output_fields": {"hashValue": "全文哈希值", "duplicateOf": "与之重复的记录列表",
                          "keepFileId": "重复组保留的记录", "duplicateSource": "重复来源（指纹库/批内）"},
        "extra_req": [],
        "desc": "全文比对识别内容完全一致的重复文本；指纹库由系统保管回传，响应返回本批新增指纹增量（newFingerprints）",
    },
    "PTt_filter_length_anomaly": {
        "seq": 14, "name": "文件长度异常过滤", "type": "规则型", "stage": "清洗·过滤", "port": 6313,
        "skippable": "是（可选）",
        "params": {},
        "output_fields": {"length": "文本长度（字符数，去首尾空白）"},
        "extra_req": [],
        "desc": "计算文本长度返回系统，过滤阈值由系统侧配置判定（算子按默认阈值500给出建议 action）",
    },
    "PTt_redact_pii": {
        "seq": 18, "name": "文件个人敏感信息检测并替换", "type": "小模型", "stage": "清洗·过滤", "port": 6314,
        "skippable": "是（可选）",
        "params": {"脱敏字段": "手机号；身份证号；地址", "脱敏方式": "掩码"},
        "output_fields": {"text": "脱敏后文本", "hits": "命中的敏感信息明细（类型/位置/原文→替换）"},
        "extra_req": [],
        "desc": "识别手机号、身份证号和地址信息，通过删除或掩码方式脱敏后放行（不隔离）",
    },
    "PTt_filter_sensitive_content": {
        "seq": 17, "name": "敏感内容检测过滤", "type": "小模型", "stage": "清洗·过滤", "port": 6315,
        "skippable": "是（可选）",
        "params": {"拦截敏感词类别": "涉黄；涉政；涉恐"},
        "output_fields": {"hits": "命中明细（位置/关键词/类别）"},
        "extra_req": [],
        "desc": "按敏感词库识别敏感内容并标明位置与类别，命中即拦截过滤；甲方微调模型到货前以词库匹配引擎提供可用壳（词库可上传覆盖）",
    },
    "PTt_chinese_tokenize": {
        "seq": 19, "name": "中文语料分词处理", "type": "规则型", "stage": "加工·分片", "port": 6316,
        "skippable": "是（可选）",
        "params": {"保留词性": "名词；动词；形容词"},
        "output_fields": {"text": "分词结果（空格分隔，按保留词性过滤）"},
        "extra_req": ["jieba>=0.42.1"],
        "desc": "jieba 分词 + 词性标注，按保留词性（名词/动词/形容词，词性族前缀 n*/v*/a*）筛选，输出空格分隔词序列",
    },
    "PTt_clean_ner_en": {
        "seq": 20, "name": "英文语料清洗与实体标注", "type": "小模型", "stage": "加工·分片", "port": 6317,
        "skippable": "是（可选）",
        "params": {},
        "output_fields": {"text": "清洗后文本（非实体词小写+词形还原，实体保留原形）",
                          "entities": "实体列表 [{text, label, start, end}]（坐标基于原文）"},
        "extra_req": ["spacy>=3.7.0", "nltk>=3.8.1"],
        "desc": "NLTK 词形还原+小写转换，spaCy 识别并标注专有名词（实体保留标准写法）；spaCy 缺席时规则引擎兜底（镜像内已装 spaCy 模型）",
    },
    "PTt_normalize_format": {
        "seq": 21, "name": "规范化数字/日期/符号格式", "type": "小模型", "stage": "加工·分片", "port": 6318,
        "skippable": "是（可选）",
        "params": {"停用词过滤": "启用"},
        "output_fields": {"text": "规范化后文本"},
        "extra_req": [],
        "desc": "中文数字转阿拉伯（日期/数量/序号上下文）、日期统一 YYYY-MM-DD、全角字母数字符号转半角（中文标点保留）、重复标点修正、停用词过滤",
    },
    "PTt_semantic_chunking": {
        "seq": 22, "name": "文本语义分块", "type": "小模型", "stage": "加工·分片", "port": 6319,
        "skippable": "是（可选-必填1个）",
        "params": {"分块策略": "章节", "最大分块长度": "512", "最小分块长度": "50"},
        "output_fields": {"texts": "分块结果列表（嵌套于记录内）"},
        "extra_req": [],
        "desc": "按章节/段落/标题策略对结构化文本语义分块，保留层级结构；超长块二次切分、过短块合并（embedding 引擎升级位预留，当前规则实现）",
    },
    "PTt_sliding_window_chunking": {
        "seq": 23, "name": "文本滑动窗口分块", "type": "规则型", "stage": "加工·分片", "port": 6320,
        "skippable": "是（可选-必填1个）",
        "params": {"窗口大小": "512", "滑动步长": "128", "重叠比例": "10%", "不足窗口处理": "保留"},
        "output_fields": {"texts": "分块结果列表"},
        "extra_req": [],
        "desc": "按窗口大小/步长/重叠比例滑窗切分无结构文本，确保片段不超过模型最大 token 限制；步长与重叠比例二选一（都传时步长优先）",
    },
    "PTt_build_qa_pairs": {
        "seq": 25, "name": "问答样本集构建", "type": "规则型", "stage": "样本构建", "port": 6321,
        "skippable": "否（必须）",
        "params": {},
        "output_fields": {"samples": "构建的问答训练样本列表（含角色标记与样本标签）"},
        "extra_req": [],
        "desc": "以已有问题/上下文/答案字段按模板组装问答训练样本（不生成问题答案，仅组装）；默认对话式模板",
    },
    "PTt_convert_mlm_format": {
        "seq": 26, "name": "掩码语言模型MLM格式转换", "type": "规则型", "stage": "样本构建", "port": 6322,
        "skippable": "是（可选）",
        "params": {"掩码比例": "15", "最大Token长度": "512", "特殊Token": "CLS/SEP/MASK", "掩码策略": "80/10/10", "随机种子": "42"},
        "output_fields": {"samples": "MLM 训练样本 [{text, maskedText, maskPositions}]"},
        "extra_req": [],
        "desc": "按掩码比例与 80/10/10 策略生成 MLM 训练样本（80%换[MASK]/10%随机词/10%保留）；tokenizer 与 #37 同源（BERT-base-Chinese），无依赖环境字符级降级",
    },
    "PTt_build_nsp_pairs": {
        "seq": 27, "name": "句子对任务NSP正负样本拼接", "type": "规则型", "stage": "样本构建", "port": 6323,
        "skippable": "是（可选）",
        "params": {"正负样本比例": "80:20", "负样本生成策略": "随机", "最大Token长度": "512", "特殊Token": "CLS/SEP", "随机种子": "42"},
        "output_fields": {"samples": "NSP 样本 [{sentenceA, sentenceB, label, formatted}]"},
        "extra_req": [],
        "desc": "连续句构成正样本、按策略取非连续句构成负样本，按比例拼接并加 [CLS]/[SEP] 标记",
    },
    "PTt_generate_tokens": {
        "seq": 37, "name": "文本生成Token序列", "type": "小模型", "stage": "数据集交付", "port": 6324,
        "skippable": "是（可选）",
        "params": {"目标模型": "bert-base-chinese", "最大Token长度": "512", "填充策略": "填充至最大长度"},
        "output_fields": {"tokens": "{input_ids, attention_mask, token_type_ids}", "truncated": "是否截断"},
        "extra_req": ["transformers>=4.36.0"],
        "desc": "BERT-base-Chinese WordPiece tokenizer（本仓自带词表，SHA256 登记快照）；超长按分片截断不静默丢弃（tags 加已截断）；需 transformers",
    },
    "PTt_check_vocab_coverage": {
        "seq": 28, "name": "词汇覆盖率校验", "type": "规则型", "stage": "数据质量评估", "port": 6325,
        "skippable": "否（必须）",
        "params": {},
        "output_fields": {"rate": "词汇覆盖率（批级，extras 内）"},
        "extra_req": ["jieba>=0.42.1"],
        "desc": "语料词汇对词典的覆盖率（词典中被语料覆盖词占比）；内置通用核心词典（jieba 词表按词频 top5000，MIT）+ dictionary 文件可覆盖；批级指标在响应 extras",
    },
    "PTt_check_domain_relevance": {
        "seq": 29, "name": "领域相关性校验", "type": "小模型", "stage": "数据质量评估", "port": 6326,
        "skippable": "否（必须）",
        "params": {"领域关键词列表": ""},
        "output_fields": {"related": "该记录是否命中关键词", "hitKeywords": "命中明细"},
        "extra_req": [],
        "desc": "含领域关键词的文档占比（关键词口径，2026-10-25 拍板；批级 relatedRatio 在 extras）；param_领域关键词列表 分号分隔",
    },
    "PTt_check_length_distribution": {
        "seq": 30, "name": "文本长度分布校验", "type": "规则型", "stage": "数据质量评估", "port": 6327,
        "skippable": "否（必须）",
        "params": {},
        "output_fields": {"length": "该记录长度"},
        "extra_req": [],
        "desc": "逐条长度 + 批级 lengthStats（min/max/avg/p50/p90/直方图，前端绘图）；达标占比按默认 100-5000/90% 给建议 action",
    },
    "PTt_check_topic_distribution": {
        "seq": 31, "name": "主题打标与分布偏科检测", "type": "小模型", "stage": "数据质量评估", "port": 6328,
        "skippable": "否（必须）",
        "params": {"主题方向": "全部"},
        "output_fields": {"topics": "该记录命中的主题标签", "mainTopic": "主线（单选）"},
        "extra_req": [],
        "desc": "内置主题表（zsy 分类体系：内容主线单选+领域多选）规则匹配打标；批级分布与偏科提示（单主题≥30%）在 extras；topic_table 文件可覆盖；embedding 升级位预留",
    },
    "PTt_filter_erroneous_text": {
        "seq": 15, "name": "文件错误文本过滤", "type": "小模型", "stage": "清洗·过滤", "port": 6329,
        "skippable": "是（可选）",
        "params": {},
        "output_fields": {"errorRate": "错别字密度（错字数/总字数）", "hits": "命中的错词明细"},
        "extra_req": [],
        "provisional": True,
        "desc": "【⚠️临时实现】错别字密度检测：规则引擎=高频错词表（Y列 Qwen3.5-2B 零样本评测通过后可换 Qwen 引擎，外壳不变）；密度>3%（默认）→低质量数据-错别字多",
    },
    "PTt_filter_semantic_anomaly": {
        "seq": 16, "name": "文件语义异常过滤", "type": "小模型", "stage": "清洗·过滤", "port": 6330,
        "skippable": "是（可选）",
        "params": {},
        "output_fields": {"fluency": "通顺度 0-1（规则特征加权）", "features": "各特征明细"},
        "extra_req": [],
        "provisional": True,
        "desc": "【⚠️临时实现】语义通顺度：规则引擎=重复n-gram/标点密度/字符多样性特征加权（Y列 Qwen3.5 logprob 打分接入位预留，阈值待评测校准）；不达标→低质量数据-语义不通",
    },
    "PTt_measure_error_rate": {
        "seq": 32, "name": "文本错误率检测", "type": "小模型", "stage": "数据质量评估", "port": 6331,
        "skippable": "否（必须）",
        "params": {"抽检样本数": "500"},
        "output_fields": {"errorRate": "该记录错误率"},
        "extra_req": [],
        "provisional": True,
        "desc": "【⚠️临时实现】抽样统计文本错误率（与 #15 共用错词引擎）；批级 avgErrorRate 在 extras；>5%→暂存隔离进人工抽检台",
    },
    "PTt_approx_dedup_large": {
        "seq": 24, "name": "大规模文本近似去重", "type": "算法", "stage": "加工·分片", "port": 6332,
        "skippable": "是（可选）",
        "params": {"相似度阈值": "80%"},
        "output_fields": {"simhash": "整篇 SimHash 指纹(64位hex)", "hammingDistance": "与重复对象的距离",
                          "duplicateOf": "疑似重复对象", "similarity": "相似度"},
        "extra_req": [],
        "provisional": True,
        "desc": "【⚠️临时实现】SimHash 近似去重（Excel 详细说明口径：1000字符分块→逐块哈希→按位投票汇总整篇指纹→海明距离判定）；命中→疑似重复打标人工确认不过滤；指纹库 simhash 格式+增量回传；百万级分布式版待与平台定",
    },
    "PTt_filter_anomalous_file": {
        "seq": 2, "name": "文本异常文件过滤", "type": "规则型", "stage": "输入核验", "port": 6302,
        "skippable": "否（必须）",
        "params": {},
        "output_fields": {"reason": "异常原因（空文件/二进制/编码异常/无法解析/文件头不合法）"},
        "extra_req": [],
        "desc": "检查文本可用性，隔离空文件、纯空白、无法解析或编码异常的文件（文件级筛查，不做内容价值判断）",
    },
    "PTt_extract_xml_body": {
        "seq": 4, "name": "XML抽出正文", "type": "规则型", "stage": "清洗·正文", "port": 6303,
        "skippable": "是（可选-必填1个）",
        "params": {"正文提取范围": "全文", "标签过滤": "启用", "属性过滤": "启用"},
        "output_fields": {"text": "抽取出的正文"},
        "extra_req": [],
        "desc": "接收 XML 文档并提取正文，解析文档结构，去除标记符号，仅保留正文文字内容",
    },
    "PTt_extract_pdf_body": {
        "seq": 5, "name": "提取PDF正文", "type": "小模型", "stage": "清洗·正文", "port": 6304,
        "skippable": "是（可选-必填1个）",
        "params": {"页码范围": "全部", "表格提取": "启用", "图片文字提取": "启用", "OCR识别": "启用"},
        "output_fields": {"text": "提取的正文", "pages": "提取的页数"},
        "extra_req": ["pypdf>=4.0.0"],
        "desc": "接收 PDF 文档并提取正文，输出纯文本内容；扫描版 PDF 需 OCR（OCR 依赖未装时明确报错，不静默输出空文档）",
    },
    "PTt_extract_docx_body": {
        "seq": 6, "name": "提取DOCX正文", "type": "规则型", "stage": "清洗·正文", "port": 6305,
        "skippable": "是（可选-必填1个）",
        "params": {"表格内容": "保留", "批注": "删除", "超链接": "删除", "图片说明文字": "保留"},
        "output_fields": {"text": "提取的正文"},
        "extra_req": ["python-docx>=1.1.0"],
        "desc": "接收 Word 文档（.docx）并提取正文（段落+表格+可选超链接），输出纯文本内容",
    },
    "PTt_extract_doc_body": {
        "seq": 7, "name": "提取DOC正文", "type": "规则型", "stage": "清洗·正文", "port": 6306,
        "skippable": "是（可选-必填1个）",
        "params": {},
        "output_fields": {"text": "提取的正文"},
        "extra_req": [],
        "desc": "接收旧版 Word 文档（.doc）并提取正文：镜像内 LibreOffice headless 转文本",
    },
    "PTt_extract_paper_body": {
        "seq": 8, "name": "提取论文场景正文", "type": "规则型", "stage": "清洗·正文", "port": 6307,
        "skippable": "是（可选-必填1个）",
        "params": {"保留章节": "摘要；关键词；引言；方法；实验；结论"},
        "output_fields": {"text": "保留章节拼接的论文正文", "sectionsKept": "保留的章节列表", "sectionsDropped": "剔除的章节列表"},
        "extra_req": ["pypdf>=4.0.0"],
        "desc": "接收论文 PDF 提取正文，保留摘要/关键词/引言/方法/实验/结论关键模块，剔除致谢、参考文献",
    },
    "PTt_remove_layout_noise": {
        "seq": 9, "name": "清除版式噪声", "type": "规则型", "stage": "清洗·正文", "port": 6308,
        "skippable": "否（必须）",
        "params": {},
        "output_fields": {"text": "清理后文本", "removedLines": "清除的噪声行数"},
        "extra_req": [],
        "desc": "去除页眉、页脚、批注、文本框等非正文内容，减少版式信息对正文的干扰",
    },
    "PTt_normalize_utf8_encoding": {
        "seq": 10, "name": "检测并归一化编码至UTF-8", "type": "规则型", "stage": "清洗·格式", "port": 6309,
        "skippable": "否（必须）",
        "params": {"编码检测方式": "charset-normalizer"},
        "output_fields": {"text": "UTF-8 归一化后的文本", "sourceEncoding": "检测到的原编码"},
        "extra_req": ["charset-normalizer>=3.1.0"],
        "desc": "检测编码格式并统一转换为 UTF-8，清除控制字符；无法识别或无法转换的文件拦截打标",
    },
    "PTt_fix_mojibake": {
        "seq": 11, "name": "检测文本乱码字符并替换", "type": "规则型", "stage": "清洗·格式", "port": 6310,
        "skippable": "否（必须）",
        "params": {"乱码处理规则": "默认清除全部无效字符"},
        "output_fields": {"text": "清理后文本", "replacedCount": "清除/替换的乱码字符数"},
        "extra_req": [],
        "desc": "检测乱码字符（ASCII 控制字符、零宽字符、替换符 U+FFFD），按配置清除或替换",
    },
    "PTt_clean_web_noise": {
        "seq": 13, "name": "网页噪声与特殊标识清理", "type": "规则型", "stage": "清洗·过滤", "port": 6311,
        "skippable": "是（可选）",
        "params": {"噪声类型": "广告；导航残片；页脚；版权声明；HTML残留", "特殊标识类型": "URL；磁力链接；App跳转链接", "URL去除": "开"},
        "output_fields": {"text": "清理后正文", "removedItems": "清除的噪声明细（类型+内容）"},
        "extra_req": [],
        "desc": "清理网页来源文本的广告/导航残片/页脚/版权声明/HTML残留，清除 URL、磁力链接、App 跳转链接等特殊标识",
    },
}

INFERENCE_TMPL = '''"""{detection} 服务入口。

薄入口：HTTP 壳与公共逻辑在 common/，核心算法在 model/network.py。
开发模式：python inference.py --port {port}
生产模式：gunicorn -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:{port} inference:app
"""

from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _path in (_ROOT, _HERE):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from common.server import create_app, run_service  # noqa: E402
from model.network import OPERATOR_CLASS  # noqa: E402

OPERATOR = OPERATOR_CLASS()
app = create_app(OPERATOR)

if __name__ == "__main__":
    run_service(OPERATOR, default_port={port})
'''


def build(detection: str) -> None:
    meta = OPERATORS[detection]
    op_dir = ROOT / detection
    if op_dir.exists():
        print(f"[SKIP] {detection} 已存在")
        return
    port, name, seq = meta["port"], meta["name"], meta["seq"]

    (op_dir / "model").mkdir(parents=True)
    (op_dir / "utils").mkdir(parents=True)
    (op_dir / "configs").mkdir(parents=True)
    (op_dir / "tests").mkdir(parents=True)
    (op_dir / "dataset" / "sample").mkdir(parents=True)
    (op_dir / "output" / "model").mkdir(parents=True)

    (op_dir / "__init__.py").write_text("", encoding="utf-8")
    (op_dir / "model" / "__init__.py").write_text(
        "from model.network import OPERATOR_CLASS\n\n__all__ = [\"OPERATOR_CLASS\"]\n",
        encoding="utf-8",
    )
    (op_dir / "utils" / "__init__.py").write_text(
        '"""工具函数库（当前核心逻辑在 model/network.py，此处预留）。"""\n', encoding="utf-8"
    )
    (op_dir / "tests" / "__init__.py").write_text("", encoding="utf-8")
    (op_dir / "inference.py").write_text(
        INFERENCE_TMPL.format(detection=detection, port=port), encoding="utf-8"
    )

    default_params = json.dumps(meta["params"], ensure_ascii=False, indent=2)
    (op_dir / "configs" / "config.yaml").write_text(
        f"# {detection} 配置（默认值与主表\"工具配置项参数设计\"列一致）\n"
        f"app:\n  name: \"{detection}\"\n  version: \"1.0.0\"\n  host: \"0.0.0.0\"\n  port: {port}\n\n"
        f"limits:\n  max_input_mb: 10\n  max_response_mb: 50\n\n"
        f"workers: 2   # 生产由 Dockerfile gunicorn 使用\n\n"
        f"# 算子默认参数（与 model/network.py default_params 保持一致）\n"
        f"params: {default_params}\n",
        encoding="utf-8",
    )

    reqs = BASE_REQUIREMENTS + meta["extra_req"]
    (op_dir / "requirements.txt").write_text(
        f"# {detection} 依赖（含共享壳 common/ 的依赖）\n" + "\n".join(reqs) + "\n",
        encoding="utf-8",
    )

    docker_extra = ""
    if detection == "PTt_extract_doc_body":
        docker_extra = "RUN apt-get update && apt-get install -y --no-install-recommends libreoffice-writer \\\n    && rm -rf /var/lib/apt/lists/*\n"
    (op_dir / "Dockerfile").write_text(
        f"# {detection} 镜像（构建上下文 = pretrain_text/ 仓库根目录）\n"
        f"# 构建：docker build -f {detection}/Dockerfile -t {detection.lower()}:1.0.0 .\n\n"
        f"FROM python:3.10-slim\n\n"
        f"LABEL description=\"预训练文本产线算子：{name}（{meta['type']}）\"\n\n"
        f"WORKDIR /srv/operator\n\n"
        f"COPY common/ /srv/common/\n"
        f"COPY {detection}/ /srv/operator/\n\n"
        f"ENV PYTHONPATH=/srv:/srv/operator \\\n    PYTHONUNBUFFERED=1 \\\n    WORKERS=2\n\n"
        f"{docker_extra}"
        f"RUN pip install --no-cache-dir -r requirements.txt\n\n"
        f"EXPOSE {port}\n\n"
        f"HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \\\n"
        f"    CMD python -c \"import urllib.request; urllib.request.urlopen('http://localhost:{port}/health')\" || exit 1\n\n"
        f"# 规范 11.2：多 worker 部署\n"
        f"CMD [\"sh\", \"-c\", \"gunicorn -k uvicorn.workers.UvicornWorker -w ${{WORKERS}} -b 0.0.0.0:{port} inference:app\"]\n",
        encoding="utf-8",
    )

    params_schema = {f"param_{k}": {"default": v} for k, v in meta["params"].items()}
    items_schema = {
        "fieldName": {"type": "string", "description": "记录标识"},
        "tags": {"type": "list", "description": "业务标签（主表拦截处理列标签原文）"},
        "action": {"type": "string", "description": "keep / remove / review"},
    }
    items_schema.update({k: {"type": "string", "description": v} for k, v in meta["output_fields"].items()})
    map_json = {
        "operator_name": detection, "detection": detection, "display_name": name,
        "tool_type": meta["type"], "stage": meta["stage"], "version": "1.0.0",
        "skippable": meta["skippable"], "api_path": "/predict", "description": meta["desc"],
        "input_schema": {
            "method": "POST", "path": f"/predict?detection={detection}",
            "content_type": "multipart/form-data",
            "form_fields": {"file": {"type": "file", "required": True,
                                     "description": "待处理文件（jsonl 每行一条记录；其他格式整体一条）"}},
            "params": params_schema,
            "limits": {"max_input_mb": 10, "max_response_mb": 50},
        },
        "output_schema": {
            "content_type": "application/json",
            "fields": {
                "code": {"type": "int", "description": "0=成功 1=失败"},
                "msg": {"type": "string", "description": "提示信息"},
                "data": {"type": "list", "items": items_schema},
            },
        },
        "error_codes": ["FILE_EMPTY", "FILE_CORRUPT", "DECODE_FAIL", "PARSE_FAIL",
                        "SIZE_EXCEEDED", "PARAM_INVALID", "MODEL_LOAD_FAIL", "INTERNAL_ERROR"],
    }
    (op_dir / "map.json").write_text(
        json.dumps(map_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    (op_dir / "README.md").write_text(
        f"# {detection} {name}\n\n"
        f"- **工具类型**：{meta['type']}　|　**所属大阶段**：{meta['stage']}　|　**是否可跳过**：{meta['skippable']}\n"
        f"- **主表编号**：#{seq}\n\n## 功能\n\n{meta['desc']}\n\n"
        f"## 接口\n\n```\nPOST /predict?detection={detection}\nContent-Type: multipart/form-data\n  file: 待处理文件\n"
        + ("".join(f"  param_{k}: {v}（默认）\n" for k, v in meta["params"].items()))
        + "```\n\n完整 schema 见 `map.json`。\n\n## 命令\n\n"
        f"```bash\npython tests/test_network.py\npython inference.py --port {port}\n"
        f"docker build -f {detection}/Dockerfile -t {detection.lower()}:1.0.0 .\n```\n\n"
        f"## 吞吐画像（联调前补实测）\n\n待测。\n\n"
        f"## 变更记录\n\n| 版本 | 日期 | 说明 |\n| --- | --- | --- |\n| 1.0.0 | 2026-10-25 | 批次1 迁移开发 |\n",
        encoding="utf-8",
    )

    (op_dir / "model" / "network.py").write_text(
        f'"""{detection}：{name}。\n\n核心逻辑迁移/开发中，见 tests/test_network.py。\n"""\n\n'
        f"from common.operator_base import Operator, OperatorOutput\n\n\n"
        f"class OPERATOR_CLASSPlaceholder(Operator):\n"
        f"    detection = \"{detection}\"\n"
        f"    name = \"{name}\"\n\n"
        f"    def process(self, records, params=None, resources=None, context=None):\n"
        f"        raise NotImplementedError\n",
        encoding="utf-8",
    )
    (op_dir / "tests" / "test_network.py").write_text(
        f'"""{detection} 单元测试（待实现）。"""\n\nimport unittest\n\n\nclass TestPlaceholder(unittest.TestCase):\n'
        f'    def test_placeholder(self):\n        self.skipTest("待实现")\n\n\nif __name__ == "__main__":\n    unittest.main()\n',
        encoding="utf-8",
    )
    (op_dir / "dataset" / "sample" / "demo.jsonl").write_text(
        '{"id": "sample_001", "text": "示例记录，待替换为该算子的真实样本。"}\n', encoding="utf-8"
    )
    print(f"[OK] {detection} -> {op_dir.name}/ (port {port})")


if __name__ == "__main__":
    targets = sys.argv[1:] or list(OPERATORS)
    for detection in targets:
        build(detection)
