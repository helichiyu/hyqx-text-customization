"""交付物生成器：逐算子生成 算子说明书 / 测试指令 / requirements.txt / Dockerfile。

用法（项目根执行）：
    python -I operators/_shared_tools/gen_docs.py          # 全部 11 个算子
    python -I operators/_shared_tools/gen_docs.py meta_clean_slice lay_page_detect

说明书八节骨架对齐兄弟项目交付样例（E14-算子说明书.md）；
测试指令按 0 前置 → 起服务 → healthz → uploadFile → predict → 产物校验 → removeFile → 负例 → 单测。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

OPERATORS_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = OPERATORS_ROOT.parent
SAMPLES = PROJECT_ROOT / "samples_pool"
SCRATCH = PROJECT_ROOT / ".scratch"

DEPENDS = {
    "web": ["fastapi==0.116.1", "uvicorn==0.51.0", "python-multipart==0.0.32",
            "starlette==0.47.3", "pydantic==2.13.4"],
    "llm": ["requests==2.34.2"],
    "pdf": ["pymupdf==1.28.2"],
    "img": ["pillow==12.0.0"],
    "test": ["pytest==8.3.4"],
}

# ---------------------------------------------------------------- 各算子规格

SPECS: dict[str, dict] = {}

SPECS["meta_clean_slice"] = {
    "name": "正文抽取与切片", "line": "文本元信息", "stage": "环节① 文档接入与切片",
    "kind": "规则（HTML 解析，不调模型）",
    "role": "阶段首算子：凭 uniqueId 取上传素材；输出供 meta_genre_judge 接续",
    "input_desc": "一个 zip 或散文件（HTML/HTM，按文件名升序处理）：网页存档",
    "output_desc": "主成果 records.jsonl（一文档一行，含标题/来源/切片数组）+ 血缘 JSONL；/predict 回 outputFile + lineageFile",
    "tech_stack": "Python 3.12、标准库 HTMLParser（解码与正文抽取）+ 正则；HTTP 层 FastAPI + uvicorn。不引入 BeautifulSoup/lxml、不调大模型",
    "definition": "交付说明环节① #1#2#4：抽取正文并清洗 → 正文校验（空白页/导航页/至少 1 段可读文本）→ 长文档按章节→段落切片（单片 ≤2000 字、重叠 200 字、超长段落硬切）",
    "boundary": "只做抽取、校验、切片三件事；新闻体裁校验是环节① #3、由下游 meta_genre_judge 承担；不做正文内容改写、不做语言校验（已确认口径：只校验正文非空）",
    "scene": "文本元信息产线第一环：把网页 HTML 变成结构化正文切片，供体裁判定与后续事实抽取消费",
    "content_src": "文本全部来自上传 HTML：只抽取与切分，不构造、不改写任何内容",
    "route": """```text
/uploadFile?uniqueId=<任务id_批次id> 上传 zip（阶段首算子）
   ↓  流式落盘 → 解压到 <INPUT_DIR>/<uniqueId>/（抹平目录层级，只留 basename）
/predict 调用（不带 inputFile，凭 uniqueId 取素材；切片参数固定不可覆盖——交付说明 §八）
   ↓  逐文件（文件名升序）：UTF-8→GB18030 两级解码（HTMLParser 解析）
   ↓  抽取：<title>（回退首个标题）、块级段落与标题标记、锚文本占比
   ↓  正文校验（顺序）：total_chars==0 → 空白页跳过
   ↓                    锚文本占比 >0.6 → 导航页跳过
   ↓                    无 ≥20 字段落 → 无有效段落跳过
   ↓  来源线索：前两段内「来源：xxx」正则捕获（供下游体裁判定）
   ↓  切片：超长段落硬切 → 章节断点（标题且当前 ≥1000 字）→ 段落贪心装片
   ↓        （单片 ≤2000 字；新片带上一片末尾 200 字重叠）
写 records.jsonl（一文档一行：docId/fileName/title/source/textLength/sliceCount/slices[]）
   ↓
写 lineage_<uniqueId>.jsonl（首行 task_lineage，其后逐样本 sample_lineage）
   ↓
isLastOperator=true：整目录收口为 <run_id>_stage_output.zip
```""",
    "route_notes": [
        ("切片参数为何固定", "交付说明 §八把切片最大长度 2,000 字、重叠 200 字（10%）列为固定项（本项考虑大模型能力），不开放 /predict 覆盖；本算子 PARAM_DEFAULTS 仅为集中可审计，不作为可调参数对外声明"),
        ("两级解码的理由", "网页存档混有 UTF-8 与 GBK 系编码，先按 UTF-8 严格解码、失败回退 GB18030，避免乱码进切片"),
        ("导航页阈值 0.6", "锚文本字符占全文字符比例超过 0.6 视为链接为主的导航/列表页（交付说明 §九：链接为主，非正文）；边界情形由后续体裁判定的模型兜底"),
    ],
    "params": [
        ("无算子参数", "—", "—", "切片 2000/200、空白·导航·段落校验阈值全部固定（configs/config.py 集中常量，交付说明 §八固定项）"),
    ],
    "upload_types": "`.html` / `.htm` / `.zip`（zip 内抹平层级，其余后缀在上传白名单层跳过并记录）",
    "sample_dir": "dataset/sample/ = 5 篇 HTML（2 新闻 + 广告产品页 + 教程页 + 导航页），覆盖通过 4 篇与三类跳过原因",
    "sample_src": "meta",
    "outputs": [
        ("records.jsonl", "UTF-8", "一文档一行：docId / fileName / title / source / textLength / sliceCount / slices[{sliceId,index,text,charCount}]"),
        ("lineage_<uniqueId>.jsonl", "UTF-8", "首行 task_lineage（算子/参数/汇总）；其后逐样本 sample_lineage（keep 带 slices 计数 / skip 带原因）"),
    ],
    "record_example": '{"docId":"news_001","fileName":"news_001.html","title":"某市地铁3号线通车","source":"某市日报","textLength":843,"sliceCount":1,"slices":[{"sliceId":"news_001-s01","index":1,"text":"6月12日，某市地铁3号线正式通车……","charCount":843}]}',
    "metrics": [
        ("离线单元测试", "6 / 6 通过", "标题抽取、GB18030 解码回退、样本池 5 篇（4 通过 + 导航页跳过）、空白/过短分支、4500 字长文硬切成 3 片且相邻片重叠 200 字、参数校验"),
        ("真实链路端到端", "5 → 4 通过 + 1 跳过", "样本池全量：导航页跳过原因正确；4 篇记录字段齐全（见 .scratch/chain_meta.py 实跑）"),
        ("确定性", "同输入两次运行产物一致", "纯标准库解析 + 贪心切片，无随机成分；不联网、不调模型"),
    ],
    "latency": "5 篇 HTML 全量 < 0.1 s（纯 CPU 解析）；不依赖网络",
    "needs_api": False,
    "deps": ["web"],
    "predict_example": '{"uniqueId":"meta001","isLastOperator":false}',
    "predict_note": "阶段首算子：不带 inputFile；本算子是产线首环，isLastOperator=false（阶段末由 meta_field_fill 收口）",
}

SPECS["meta_genre_judge"] = {
    "name": "新闻体裁判定", "line": "文本元信息", "stage": "环节① 文档接入与切片",
    "kind": "文本大模型（规则粗筛 + 大模型边界判定）",
    "role": "链路第 2 环：接 meta_clean_slice 产物（inputFile）；输出供 meta_fact_extract 接续",
    "input_desc": "上游 records.jsonl（一文档一行，含 slices）；或打包该文件的 zip",
    "output_desc": "records.jsonl（新闻文档，genre 字段并入）+ review.jsonl（低置信/解析失败待复核）+ 血缘 JSONL",
    "tech_stack": "Python 3.12、requests（OpenAI 兼容 chat/completions，JSON mode）+ ThreadPoolExecutor 受限并发；HTTP 层 FastAPI + uvicorn。模型 deepseek-ai/DeepSeek-V3.2（硅基流动）",
    "definition": "交付说明环节① #3 + §4.1 Prompt 原文：四条标准（事件性/时效性/事实性/公共传播性）同时满足才算新闻；输出 is_news / category / 四条件 / 置信度 / 依据",
    "boundary": "规则粗筛只过滤明显非新闻（教程类标题、广告关键词），边界情形全部交给模型；置信度 <0.8 一律进复核（不论是否新闻）；≥0.8 且非新闻才跳过。不做实体抽取、不做时间抽取（环节②职责）",
    "scene": "文本元信息产线的总闸：非新闻文档在此出局，只有新闻进事实抽取与三组补全",
    "content_src": "判定结论由模型基于上传正文生成；正文本身原样透传给下游，本算子不改正文",
    "route": """```text
/predict（inputFile = 上游 meta_clean_slice 输出目录）
   ↓  读 records.jsonl（一文档一行）
规则粗筛（零成本出局，命中即跳过不调模型）：
   ↓  标题含「教程/入门指南/五分钟学会/实战指南」→ 跳过：规则粗筛-教程类
   ↓  前 800 字含「立即购买/好评率/七天无理由/限时特惠/已售/原价」→ 跳过：规则粗筛-广告/产品页
模型判定（未命中粗筛的文档，并发 4–8，ThreadPoolExecutor）：
   ↓  输入：标题 + 来源 + 正文前 800 字（§4.1 User 模板）
   ↓  System：§4.1 原文（四条标准/算新闻/不算新闻/边界/输出 JSON）
   ↓  JSON 解析失败重试 1 次（传输层 429/5xx 重试 2 次由公共 client 承担）
   ↓  置信度截断到 [0, 0.98]；category 越枚举兜底「其他」
三分路由：
   ↓  解析仍失败            → review.jsonl（模型输出解析失败），不进下游
   ↓  置信度 < 0.8          → review.jsonl（置信度低于阈值），不进下游
   ↓  ≥0.8 且 is_news=false → 跳过清单（非新闻体裁）
   ↓  ≥0.8 且 is_news=true  → records.jsonl（genre 字段并入原文档记录）
写 records.jsonl / review.jsonl / lineage
```""",
    "route_notes": [
        ("为什么规则粗筛在前", "教程、广告两类在高置信下模型也能判对，但纯规则即可零成本出局；粗筛关键词刻意收窄（只过滤「明显非新闻」），避免误杀边界文档——误杀代价高于多花一次模型调用"),
        ("复核口径", "交付说明 §4.1：置信度 <0.8 → 进复核（不论是否新闻）——所以低置信的疑似广告也进复核而不是直接跳过，由人工裁定"),
        ("category 枚举", "消息/通讯/特写/专访/通报/评论/广告/教程/通知/其他；模型越枚举时兜底「其他」并保留原值进 reason，不因枚举违规重试（判定结论本身可用）"),
    ],
    "params": [
        ("confidence_threshold", "Number", "否", "体裁判定置信度阈值，默认 0.8（交付说明 §八：固定 0.8，此处仅为任务级预留）；低于阈值进复核"),
        ("concurrency", "Number", "否", "模型调用并发，默认 4，上限 8（交付说明 §八：并发数 4–8）"),
    ],
    "upload_types": "`.jsonl` / `.zip`（本算子为链路中段，正常形态经 inputFile 接续，不走 uploadFile）",
    "sample_dir": "dataset/sample/ = 上游真实产物 records.jsonl（4 篇：2 新闻 + 广告 + 教程）",
    "sample_src": None, "sample_from": ("smoke_meta/clean_out", ["records.jsonl"]),
    "outputs": [
        ("records.jsonl", "UTF-8", "新闻文档一文档一行：上游字段 + genre{is_news,category,conditions,confidence,reason,evidence,screening}"),
        ("review.jsonl", "UTF-8", "待复核文档：完整记录 + reviewReason（置信度低于阈值 / 模型输出解析失败）"),
        ("lineage_<run_id>.jsonl", "UTF-8", "首行 task_lineage；其后逐样本 keep（带 genre_confidence）/ skip / review"),
    ],
    "record_example": '{"docId":"news_001",...,"genre":{"is_news":true,"category":"消息","conditions":{"event":true,"timeliness":true,"factual":true,"public":true},"confidence":0.98,"reason":"主体+事件+时间+地点齐备","evidence":["6月12日某市地铁3号线通车"],"screening":"model"}}',
    "metrics": [
        ("离线单元测试", "4 / 4 通过", "规则粗筛命中不调模型（monkeypatch 断言）、新闻保留/非新闻跳过/低置信复核三分路由、解析失败进复核、缺输入报错"),
        ("真实 API 冒烟", "2 新闻判定正确（消息，0.98/0.95）", "广告页与教程页被规则粗筛直接跳过（零模型调用）；分类、四条件、依据句齐全"),
        ("重试口径", "传输 429/5xx 重试 2 次；JSON 解析失败重试 1 次", "公共 llm_client 统一实现（.scratch/verify_shared_client.py 验证）"),
    ],
    "latency": "单篇判定约 3–8 s（DeepSeek-V3.2）；并发 4 时 4 篇约 10 s",
    "needs_api": True,
    "deps": ["web", "llm"],
    "predict_example": '{"inputFile":"<上游 outputFile>","isLastOperator":false}',
    "predict_note": "链路中段：inputFile 指向上游 meta_clean_slice 响应的 data.outputFile",
}

SPECS["meta_fact_extract"] = {
    "name": "新闻事实抽取", "line": "文本元信息", "stage": "环节② 事实抽取",
    "kind": "文本大模型（按片抽取 + 规则合并去重）",
    "role": "链路第 3 环：接 meta_genre_judge 产物；输出供 meta_field_fill 接续",
    "input_desc": "上游 records.jsonl（新闻文档，含 slices 与 genre）",
    "output_desc": "records.jsonl（facts 字段并入）+ review.jsonl（来源缺失/冲突/低置信待复核）+ 血缘 JSONL",
    "tech_stack": "Python 3.12、requests（JSON mode）+ ThreadPoolExecutor；HTTP 层 FastAPI + uvicorn。模型 deepseek-ai/DeepSeek-V3.2",
    "definition": "交付说明环节② + §4.2 Prompt 原文：抽取数据来源类型、发布时间候选、人物/地点/组织；时间保留原文粒度；同名实体分别列出；同字段多候选保留并标 conflict",
    "boundary": "只抽文中明确出现的信息，不推断不补全；抽不到返回空数组不编造。冲突不阻断（进复核由人裁定）。切片只用于读；合并后交下游文档级补全",
    "scene": "把新闻正文压成可审计的事实清单（来源/时间/实体），作为三组补全的依据，避免补全部编造",
    "content_src": "事实条目由模型基于上传正文生成，每条带原文短句与位置证据；正文原样透传",
    "route": """```text
/predict（inputFile = 上游 meta_genre_judge 输出目录）
   ↓  读 records.jsonl；逐文档逐片并发抽取（片间并发、文档间并发，总并发 4–8）
每片（§4.2 Prompt 原文）：
   ↓  输入：标题 + 该片正文；输出：source_type / time_candidates / entities / conflicts / uncertain
   ↓  规范化：置信度截断 [0,0.98]；来源类型越枚举置 null；实体 kind 越枚举兜底 org
   ↓  单片两次解析失败 → 该片失败（不吞），其余片继续，uncertain 记录
文档级合并（纯规则）：
   ↓  来源类型：按值去重留最高置信；多值 → conflict
   ↓  时间候选：按值去重留最高置信；多值 → conflict{field:time, candidates, reason}
   ↓  实体：按 mention 去重留最高置信；同名不同 kind → uncertain
   ↓  extractConfidence = 来源/时间/实体置信度最低分（交付说明 §五口径）
复核分流（冲突不阻断）：
   ↓  全部切片失败          → failed + review（不进下游）
   ↓  来源类型缺失 / 有冲突 / 最低置信 <0.8 → review + 继续下游
写 records.jsonl（facts 并入）/ review.jsonl / lineage
```""",
    "route_notes": [
        ("为何按片抽再合并", "交付说明 §4.2：长文按切片分别抽取，合并时按 mention/时间值去重；单片上下文小、抽取稳定，合并交给确定性规则（可审计、可复现）"),
        ("冲突标记而非裁决", "交付说明环节②：时间候选冲突 → 标记，复核时裁定。算法侧不猜哪个对，把候选与理由摆给复核"),
        ("抽取置信度口径", "交付说明 §五：抽取置信度 = 来源/时间/实体最低分；任一类抽不到不计入最低分（空数组不拖垮整体）"),
    ],
    "params": [
        ("confidence_threshold", "Number", "否", "抽取质量阈值，默认 0.8（交付说明 §八：抽取/补全共用 0.80，任务级可调）；低于进复核"),
        ("concurrency", "Number", "否", "模型调用并发，默认 4，上限 8"),
    ],
    "upload_types": "`.jsonl` / `.zip`（链路中段，经 inputFile 接续）",
    "sample_dir": "dataset/sample/ = 上游真实产物 records.jsonl（2 篇新闻，含 genre）",
    "sample_src": None, "sample_from": ("smoke_meta/genre_out", ["records.jsonl"]),
    "outputs": [
        ("records.jsonl", "UTF-8", "一文档一行：上游字段 + facts{sourceType,timeCandidates[],entities[],conflicts[],uncertain[],extractConfidence}"),
        ("review.jsonl", "UTF-8", "待复核文档 + reviewReason（来源类型缺失 / 候选冲突待裁定 / 抽取置信度低于阈值 / 全部切片失败）"),
        ("lineage_<run_id>.jsonl", "UTF-8", "逐样本 keep（带 extract_confidence/entities/conflicts 计数）/ fail"),
    ],
    "record_example": '{"docId":"news_001",...,"facts":{"sourceType":{"value":"官方媒体","evidence":"来源：某市日报","confidence":0.95},"timeCandidates":[{"value":"2026年6月12日","granularity":"日","position":"第1段","confidence":0.98},{"value":"2021年3月","granularity":"月","position":"第3段","confidence":0.98}],"entities":[{"mention":"张伟","kind":"person","confidence":0.9}],"conflicts":[{"field":"time","candidates":["2026年6月12日","6月12日","2021年3月"],"reason":"多切片时间候选不一致"}],"uncertain":[],"extractConfidence":0.95}}',
    "metrics": [
        ("离线单元测试", "6 / 6 通过", "两片合并去重与 time conflict 标记、全部切片失败仅复核、来源缺失复核且继续、置信度 1.5 截断 0.98、单片解析失败重试 1 次且 uncertain 记录、缺输入报错"),
        ("真实 API 冒烟", "两篇抽取正确", "news_001 抽出 3 个时间候选（含开工/通车两个时间）并正确标 conflict、7 个实体分 person/place/org；news_002 单候选无冲突"),
        ("抽取置信度", "0.95 / 0.95", "来源/时间/实体最低分口径与交付说明 §五一致"),
    ],
    "latency": "单片抽取约 3–8 s；2 篇（4 片）并发 4 约 15 s",
    "needs_api": True,
    "deps": ["web", "llm"],
    "predict_example": '{"inputFile":"<上游 outputFile>","isLastOperator":false}',
    "predict_note": "链路中段：inputFile 指向 meta_genre_judge 的 data.outputFile",
}

SPECS["meta_field_fill"] = {
    "name": "元信息三组补全", "line": "文本元信息", "stage": "环节③ 元信息补全（产线末位）",
    "kind": "文本大模型（文档级一次补全 + 字段校验）",
    "role": "链路第 4 环（末位）：接 meta_fact_extract 产物；isLastOperator=true 收口阶段 zip",
    "input_desc": "上游 records.jsonl（含 facts 事实清单）",
    "output_desc": "records.jsonl（数据集行：16 字段 + 两个置信度 + 复核状态）+ fields_detail.jsonl（逐字段置信度明细）+ review.jsonl + 血缘 JSONL + 阶段 zip",
    "tech_stack": "Python 3.12、requests（JSON mode，max_tokens 8192）；HTTP 层 FastAPI + uvicorn。模型 deepseek-ai/DeepSeek-V3.2",
    "definition": "交付说明环节③ + §4.3 Prompt 原文：三组 16 字段（结构化 4 + 基础 6 + 相关 6）逐字段置信度；结构化字段以事实清单为依据不得编造；没有的字段写「无/不适用」",
    "boundary": "补全按文档级一次完成（切片只用于读，交付说明已确认口径）；知识点少于 3 个按实际数量输出并在 uncertain 说明；价值观/历史/国家/宗教是正常数据集字段（已确认口径），不做特殊处理",
    "scene": "文本元信息产线终点：一文档一行的数据集行，字段与交付说明 §五数据集明细一致",
    "content_src": "16 字段值由模型基于标题、正文（截断 6000 字）与事实清单生成；事实清单只作依据不改写",
    "route": """```text
/predict（inputFile = 上游 meta_fact_extract 输出目录；isLastOperator=true）
   ↓  逐文档（并发 4–8）：标题 + 正文（多片拼接截断 6000 字）+ 事实清单 JSON
   ↓  §4.3 System（字段定义/规则/输出 JSON）一次调用出 16 字段
   ↓  JSON 解析失败重试 1 次；仍失败 → failed + review（不进数据集）
字段校验与规范化（规则）：
   ↓  缺字段 / 值为空 → 兜底「无」（列表字段兜底 []）并记 problem
   ↓  知识层次越枚举 → 「无」；价值观越枚举 → 「中性」（均记 problem）
   ↓  列表字段收到标量 → 包装成单元素列表
   ↓  逐字段置信度截断 [0,0.98]；fillConfidence = 16 字段最低分（§五口径）
复核分流：
   ↓  有 problem / fillConfidence <0.8 → reviewStatus=待复核（数据集行保留）
   ↓  无问题 → reviewStatus=未进入复核，revisionStatus=—
写 records.jsonl（数据集行）/ fields_detail.jsonl（逐字段置信度 + uncertain + problems）
写 review.jsonl / lineage；isLastOperator=true 收口 <run_id>_stage_output.zip
```""",
    "route_notes": [
        ("文档级一次补全", "交付说明环节③：切片只用于读，事实合并后文档级一次补全——避免逐片补全再投票的复杂度与不一致"),
        ("「无/不适用」是合法值", "交付说明 §4.3 规则 3：确实没有的字段写「无」或「不适用」，不要留空也不要硬编；校验层把缺失字段兜底为「无」而不是重试，就是这个口径的落地"),
        ("两个置信度并列", "抽取置信度（环节② facts.extractConfidence 透传）+ 补全置信度（本环节 16 字段最低分），对应数据集明细的两列（已确认口径 12）"),
    ],
    "params": [
        ("confidence_threshold", "Number", "否", "补全质量阈值，默认 0.8（与抽取共用 0.80，任务级可调）；fillConfidence 低于进复核"),
        ("max_text_chars", "Number", "否", "送模型的正文最大字符，默认 6000（防超长上下文；须 ≥500）"),
        ("concurrency", "Number", "否", "模型调用并发，默认 4，上限 8"),
    ],
    "upload_types": "`.jsonl` / `.zip`（链路中段，经 inputFile 接续）",
    "sample_dir": "dataset/sample/ = 上游真实产物 records.jsonl（2 篇，含 facts）",
    "sample_src": None, "sample_from": ("smoke_meta/fact_out", ["records.jsonl"]),
    "outputs": [
        ("records.jsonl", "UTF-8", "数据集行：docId + structured(4) + basic(6) + related(6) + extractConfidence + fillConfidence + reviewStatus + revisionStatus（对齐 §五样例）"),
        ("fields_detail.jsonl", "UTF-8", "逐字段置信度 fieldConfidences + uncertain + problems（复核查看用，不进数据集）"),
        ("review.jsonl", "UTF-8", "待复核行 + reviewReason（字段缺失/枚举非法/置信度输出失败/低于阈值）"),
        ("<run_id>_stage_output.zip", "zip", "isLastOperator=true 时整目录收口（阶段最终产物）"),
    ],
    "record_example": '{"docId":"news_002","structured":{"数据来源类型":"企业官网","可能的发布时间":"2026年7月3日","涉及人物、地点或组织":["某新能源科技公司","某农业大学","会展中心"],"时空变迁信息":"无"},"basic":{"知识层次":"技术应用","涉及的知识点列表":["战略合作","智能农机","地理标志产业","科研平台建设"],"主要一级行业":"制造业","行业场景":"新能源产业研发与人才引进","行业类型":"新能源","涉及的角色列表":["企业（新能源科技）","高校（农业大学）"]},"related":{"文章风格":"客观报道","内容类别":"企业动态","价值观":"褒","历史关联":"无关联","国家关联":"中国","宗教关联":"无"},"extractConfidence":0.95,"fillConfidence":0.8,"reviewStatus":"未进入复核","revisionStatus":"—"}',
    "metrics": [
        ("离线单元测试", "4 / 4 通过", "数据集行与 §五样例字段一致、缺字段兜底/枚举纠正/低置信复核、模型失败仅进失败清单、缺输入报错"),
        ("真实 API 冒烟", "两篇 16 字段齐全", "news_002 fillConfidence=0.8 未进复核；news_001 fillConfidence=0.7 正确进待复核；价值观/知识层次枚举值合法"),
        ("端到端链路", "5 HTML → 2 数据集行", ".scratch/chain_meta.py：uploadFile → predict×4 → stage zip 全通，数据集行字段齐全"),
    ],
    "latency": "单篇一次调用约 5–25 s（16 字段输出较长）；2 篇并发约 30 s",
    "needs_api": True,
    "deps": ["web", "llm"],
    "predict_example": '{"inputFile":"<上游 outputFile>","isLastOperator":true}',
    "predict_note": "产线末位：isLastOperator=true，输出收口为阶段 zip",
}

SPECS["lay_page_render"] = {
    "name": "版面分页渲染", "line": "复杂版面", "stage": "环节① 文档接入与分页",
    "kind": "规则（PDF 渲染，不调模型）",
    "role": "阶段首算子：凭 uniqueId 取上传素材；输出供 lay_page_detect 接续",
    "input_desc": "一个 zip 或散文件（PDF，按文件名升序处理）",
    "output_desc": "pages/<docId>/ 页图 PNG + records.jsonl（含 PageManifest 与页清单）+ 血缘 JSONL",
    "tech_stack": "Python 3.12、PyMuPDF（打开校验 + 逐页 pixmap 渲染）+ hashlib（SHA-256）；HTTP 层 FastAPI + uvicorn。不引入 OCR/深度学习框架",
    "definition": "交付说明环节① #2–#6：打开 PDF 校验加密/损坏 → 逐页渲染（默认 150 DPI）→ 生成 PageManifest（docId、pageCount、format、pageRange、checksum）→ 校验页数 >0 → 页图 + 页号交环节②",
    "boundary": "只做渲染与清单，不做版面检测（环节②职责）；单页渲染失败只跳过该页进失败页清单，不牵连整份；整份加密/损坏/0 页进失败清单（任务待处理口径）",
    "scene": "复杂版面产线第一环：把 PDF 变成逐页图片与可校验的页清单",
    "content_src": "页图由上传 PDF 渲染生成（MuPDF pixmap）；checksum 为 PDF 原文件 SHA-256，不改动上传原件",
    "route": """```text
/uploadFile?uniqueId=<任务id_批次id> 上传 zip（阶段首算子）
   ↓  流式落盘 → 解压到 <INPUT_DIR>/<uniqueId>/
/predict（dpi 可覆盖，默认 150；image_format 默认 png）
   ↓  逐 PDF（文件名升序）：
   ↓    open_pdf 校验：加密 / 损坏 / 0 页 → PdfError → 失败清单（整份出局）
   ↓    build_manifest：docId / pageCount / format / pageRange=[1,N] / SHA-256
   ↓    逐页渲染：pixmap(matrix=dpi/72) → pages/<docId>/<docId>_p000N.png
   ↓      单页渲染异常 → 该页进 failedPages（failedPages 不送环节②），其余页照常
   ↓      全部页失败 → PdfError（整份出局）
写 records.jsonl：{docId, fileName, manifest, pages[{pageNo,image,width,height}], failedPages[]}
写 lineage（keep 带 pages/failed_pages 计数，fail 带原因）
```""",
    "route_notes": [
        ("DPI 默认 150", "交付说明 §八：渲染 DPI 默认 150、可配 150–200（任务快照）；本算子放开 72–300 校验区间，默认与交付口径一致"),
        ("单页失败隔离", "交付说明环节①：单页渲染失败 → 失败页清单，不送环节②。渲染循环逐页 try/except，一页失败不影响其余页；环节② 会把 failedPages 汇总进自己的失败页清单"),
        ("checksum 用途", "页清单的 SHA-256 供平台核对素材唯一性与重跑一致性（同一 PDF 重跑 checksum 不变）"),
    ],
    "params": [
        ("dpi", "Number", "否", "渲染 DPI，默认 150（交付说明建议 150–200）；须在 72–300"),
        ("image_format", "String", "否", "页图格式，默认 png；可选 jpg"),
    ],
    "upload_types": "`.pdf` / `.zip`",
    "sample_dir": "dataset/sample/ = layout_sample.pdf（3 页：双栏+图+表+公式+空白页）+ encrypted.pdf（加密负例）",
    "sample_src": "lay",
    "outputs": [
        ("pages/<docId>/*.png", "PNG", "逐页渲染图，文件名 <docId>_p<页号4位>.png，尺寸随 DPI"),
        ("records.jsonl", "UTF-8", "一 PDF 一行：manifest{docId,pageCount,format,pageRange,checksum} + pages[] + failedPages[{pageNo,reason}]"),
        ("lineage_<uniqueId>.jsonl", "UTF-8", "逐 PDF keep（带 pages 计数）/ fail（加密/损坏/0 页/全部页失败）"),
    ],
    "record_example": '{"docId":"layout_sample","fileName":"layout_sample.pdf","manifest":{"docId":"layout_sample","pageCount":3,"format":"pdf","pageRange":[1,3],"checksum":"<sha256-64位>"},"pages":[{"pageNo":1,"image":"pages/layout_sample/layout_sample_p0001.png","width":1240,"height":1754}],"failedPages":[]}',
    "metrics": [
        ("离线单元测试", "6 / 6 通过", "渲染 + PageManifest 字段、加密失败、损坏与 0 页失败、单页失败隔离（第 2 页炸仍出 1/3 页）、全部页失败整份出局、参数校验"),
        ("真实链路", "2 PDF → 1 成功（3 页）+ 1 加密失败", "加密 PDF 正确进失败清单；页图尺寸 1240x1754（150DPI A4）"),
        ("幂等", "同一 PDF 两次渲染页图字节一致", "MuPDF 确定性渲染，无随机成分"),
    ],
    "latency": "3 页 PDF 渲染约 1 s（150 DPI，纯 CPU）；不依赖网络",
    "needs_api": False,
    "deps": ["web", "pdf"],
    "predict_example": '{"uniqueId":"lay001","isLastOperator":false}',
    "predict_note": "阶段首算子：不带 inputFile；环节② lay_page_detect 接续",
}

SPECS["lay_page_detect"] = {
    "name": "逐页版面检测", "line": "复杂版面", "stage": "环节② 逐页检测 + 环节③ 质量校验汇总（产线末位）",
    "kind": "视觉大模型（逐页检测）+ 规则分流",
    "role": "链路第 2 环（末位）：接 lay_page_render 产物；isLastOperator=true 收口",
    "input_desc": "上游 records.jsonl + pages/ 页图（inputFile 指向上游输出目录）",
    "output_desc": "records.jsonl（一页一行数据集）+ review.jsonl（问题页）+ visual/ 框选图层 + 血缘 JSONL + 阶段 zip",
    "tech_stack": "Python 3.12、requests（VL 模型多模态调用）+ Pillow（框选图层）+ ThreadPoolExecutor；HTTP 层 FastAPI + uvicorn。模型 Qwen/Qwen3-VL-8B-Instruct（硅基流动）",
    "definition": "交付说明环节②③ + §4.1/§4.2 Prompt 原文：逐页输出元素（type/bbox/readingOrder/structureTree/双置信度）→ §4.6 后处理校验 → 规则分流（六类）→ 汇总（环节③只汇总不自检）",
    "boundary": "不做 OCR 不提取文字（§4.1 硬性约束 2）；只排本页阅读顺序；规则分流只标记不裁决（复核人工裁定）；系统性错误重跑②时旧复核单作废是平台侧职责",
    "scene": "复杂版面产线核心环：页图 → 结构化版面元素 + 问题页分流，一页一行进数据集",
    "content_src": "元素框与类型由模型基于页图判定；页图原样透传，另生成框选图层（原图 + 框线，复核可视化用）",
    "route": """```text
/predict（inputFile = 上游 lay_page_render 输出目录；isLastOperator=true）
   ↓  读 records.jsonl；上游 failedPages 直接汇入失败页清单（不送检测）
逐页并发（4–8，每页一次 VL 调用，长边压到 1600px）：
   ↓  §4.1 System（元素类型 10 枚举/bbox 0-1000/阅读顺序/结构树/双置信度）
   ↓  §4.2 User：「这是文档的第 N 页…」
§4.6 后处理校验（不合法整次重试 1 次；传输层重试由公共 client 承担）：
   ↓  JSON 可解析 / pageNo 与请求一致（模型漏回填时本端补齐）/ type 在枚举 /
   ↓  bbox 四值 0–1000 且 x1<x2 y1<y2 / readingOrder 正整数
规范化：elementId 重写 p{页}-e{序}；bbox 越界截断并记 clipped
规则分流（六类，命中 → 待复核，不阻断）：
   ↓  空页（elements=[]）/ 框选偏低 / 判定偏低（页内最小分 <0.8）
   ↓  重叠（任意两框 IoU>0.3）/ 越界（发生截断）/ 顺序冲突（重号或缺号）
   ↓  页图 + 框选图层 → visual/<docId>_p000N.png
数据集行（一页一行）：pageId / 元素数组 / structureTree / readingOrder /
   confidence{bbox,type}=页内最小分 / lowConfidenceCount / lowConfidenceReasons
模型调用或输出持续非法 → 失败页清单（该页不进数据集）
isLastOperator=true 收口阶段 zip
```""",
    "route_notes": [
        ("六类分流全部落地", "交付说明环节②规则：框选 <0.8 或判定 <0.8、重叠 IoU>0.3、越界、顺序重号/缺号、空页 → 进复核。越界在规范化层截断修正并标记（框可用但需人看）；顺序冲突不阻断（§4.6：交给规则分流）"),
        ("bbox 0–1000 归一化", "交付说明 §4.1 坐标口径；Qwen3-VL grounding 冒烟已验证该坐标系稳定（6 元素类型/bbox/顺序全对）。框选图层按页图实际尺寸换算回像素绘制"),
        ("环节③只汇总", "交付说明环节③：汇总元素结果、失败页清单、复核结论，不做自检——本算子输出即汇总形态（一页一行 + 失败页清单 + 复核清单），问题页只追加平台复核单"),
        ("长边 1600px", "交付说明 §4.5 建议 1600–2000px；实测 2000px 单页 60s 超时、1600px 约 17s，取下限保证 60s 超时预算内稳定"),
    ],
    "params": [
        ("confidence_threshold", "Number", "否", "低置信阈值（框选/判定共用），默认 0.8（交付说明 §八：任务级可调）"),
        ("iou_threshold", "Number", "否", "重叠判定 IoU 阈值，默认 0.3（交付说明 §八：固定 0.3，此处仅预留）"),
        ("concurrency", "Number", "否", "逐页调用并发，默认 4，上限 8"),
        ("draw_overlay", "Boolean", "否", "是否生成框选图层，默认 true"),
    ],
    "upload_types": "`.jsonl` / `.zip`（链路中段，经 inputFile 接续）",
    "sample_dir": "dataset/sample/ = 上游真实产物（records.jsonl + pages/ 页图 3 张）",
    "sample_src": None, "sample_from": ("smoke_lay/render_out", None),
    "outputs": [
        ("records.jsonl", "UTF-8", "一页一行：pageId=docId-#页号 / elementCount / elements[{elementId,type,bbox,readingOrder,bboxConf,typeConf}] / structureTree / readingOrder / confidence / lowConfidenceCount / lowConfidenceReasons / reviewStatus"),
        ("visual/*.png", "PNG", "页图 + 红框 + elementId:type 标注（复核可视化）"),
        ("review.jsonl", "UTF-8", "问题页整行 + reviewReason（六类规则命中项，分号连接）"),
        ("<run_id>_stage_output.zip", "zip", "isLastOperator=true 时整目录收口"),
    ],
    "record_example": '{"pageId":"layout_sample-#1","docId":"layout_sample","pageNo":1,"elementCount":6,"elements":[{"elementId":"p1-e1","type":"header","bbox":[66,25,231,38],"readingOrder":1,"bboxConf":0.95,"typeConf":0.95}],"structureTree":[],"readingOrder":[1,2,3,4,5,6],"confidence":{"bbox":0.9,"type":0.9},"lowConfidenceCount":0,"lowConfidenceReasons":"","reviewStatus":"未进入复核","revisionStatus":"—"}',
    "metrics": [
        ("离线单元测试", "4 / 4 通过", "六类分流规则各命中一次（干净/框选低/判定低/重叠/越界截断/顺序重号/空页）+ 模型失败页 + 渲染失败页汇入；pageNo 不符重试 1 次后进失败页；IoU 直测"),
        ("真实 API 冒烟", "3 页全对", "p1 双栏 6 元素（header/heading/body/figure/body/footer）类型与顺序全对；p2 表+公式识别；p3 空页正确进复核"),
        ("端到端链路", ".scratch/chain_lay.py 全通", "uploadFile → render → detect → stage zip；一页一行 3 行 + 框选图层 2 张（空页无图层）"),
    ],
    "latency": "单页约 17 s（Qwen3-VL-32B，1600px）；3 页并发 4 约 40 s",
    "needs_api": True,
    "deps": ["web", "llm", "img"],
    "predict_example": '{"inputFile":"<上游 outputFile>","isLastOperator":true}',
    "predict_note": "产线末位：isLastOperator=true 收口阶段 zip",
}

SPECS["fml_formula_locate"] = {
    "name": "公式区域定位与裁切", "line": "公式文本", "stage": "环节① 素材接入与定位",
    "kind": "规则（PDF 渲染）+ 视觉大模型（grounding 定位）",
    "role": "阶段首算子：凭 uniqueId 取上传素材；输出供 fml_formula_recognize 接续",
    "input_desc": "一个 zip 或散文件（PDF：混合文档，含正文与公式）",
    "output_desc": "crops/ 公式裁切图 + pages/ 页图 + records.jsonl（FormulaInstance 登记）+ 血缘 JSONL",
    "tech_stack": "Python 3.12、PyMuPDF（渲染 + 页文本块）+ Pillow（裁切）+ requests（VL grounding）；HTTP 层 FastAPI + uvicorn。模型 Qwen/Qwen3-VL-8B-Instruct",
    "definition": "交付说明环节① #1–#3：接收校验素材 → 定位混合文档中的公式区域（只处理独立成行或带编号的公式，行内公式不处理）→ 裁切并登记可回溯公式实例（页码、bbox、上下文文本范围）",
    "boundary": "定位 Prompt 由本侧按环节①职责自行设计（交付说明只给识别 Prompt §4.2）；单页定位失败跳过该页并记录；裁切/坐标校验失败跳过该实例并记录；整份 0 公式按交付说明进失败清单（任务待处理口径）",
    "scene": "公式文本产线第一环：从混合 PDF 里把独立公式连图带上下文摘出来，登记成可回溯实例",
    "content_src": "裁切图与上下文文本全部来自上传 PDF；bbox/hasNumber/置信度由模型基于页图判定",
    "route": """```text
/uploadFile?uniqueId=<任务id_批次id> 上传 zip（阶段首算子）
   ↓  流式落盘 → 解压到 <INPUT_DIR>/<uniqueId>/
/predict（dpi 默认 150；max_context_chars 默认 2000 固定口径）
   ↓  逐 PDF：open_pdf 校验（加密/损坏/0 页 → 失败清单）
   ↓  逐页渲染 150 DPI 页图；单页渲染失败 → 跳过该页
逐页定位（并发 4–8，每页一次 VL 调用，长边 1600px）：
   ↓  System：只定位独立成行/带编号公式；行内不算；bbox 0–1000 含编号；
   ↓        宁少勿多（漏检代价低于误检）；空页输出 formulas:[]
   ↓  输出非法重试 1 次；单页定位失败 → 跳过该页并记录
逐实例：
   ↓  坐标校验：四值 0–1000、x1<x2<y1<y2、面积 ≥20（归一化坐标）；非法 → 跳过并记录
   ↓  裁切：页图按 bbox 换算像素裁出 crops/<docId>/<实例>.png；过小 → 跳过并记录
   ↓  上下文：PyMuPDF 页文本块（y 序），取公式前后各至多 2 段，总长 ≤2000 字；
   ↓           章节标题取全页最大字号文本块
写 records.jsonl：FormulaInstance{instanceId,pageNo,bbox,bboxPixel,hasNumber,
   locateConfidence,crop,chapterTitle,contextText}
整份 0 实例 → 失败清单（原因：未定位到公式）
```""",
    "route_notes": [
        ("定位 Prompt 自行设计的口径", "交付说明 §四只给识别 Prompt；定位按环节①职责（只处理独立成行或带编号的公式）设计 System，输出仅 bbox/hasNumber/置信度，不做识别"),
        ("行内公式不处理", "交付说明环节①范围注：Prompt 明确「行内公式（嵌在句子里的符号）不要定位」，实测样本中行内提及的公式未被定位，独立 3 个公式全部定位"),
        ("上下文 ≤2000 字", "交付说明 §4.3：contextText 取公式前后各 1–2 段，总长 ≤2000 字；实现取与公式纵向最近文本块向前后各扩至多 2 段、超长截断"),
        ("回溯字段口径", "页码/bbox/上下文范围只用于内部回溯（环节②消费），最终数据集不展示（§五）——本算子产物保留全部回溯字段，裁剪发生在 fml_formula_recognize"),
    ],
    "params": [
        ("dpi", "Number", "否", "页图渲染 DPI，默认 150；须在 72–300"),
        ("max_context_chars", "Number", "否", "上下文文本上限，默认 2000（交付说明固定 2000，此处仅预留）；须 ≥200"),
        ("concurrency", "Number", "否", "逐页定位并发，默认 4，上限 8"),
    ],
    "upload_types": "`.pdf` / `.zip`",
    "sample_dir": "dataset/sample/ = formula_sample.pdf（第二章：无编号分式+根式、带编号 E=mc²(2-3)、两行配方、行内提及不处理、第 2 页无公式）",
    "sample_src": "fml",
    "outputs": [
        ("pages/<docId>/*.png", "PNG", "逐页渲染图（定位与裁切的底图）"),
        ("crops/<docId>/<instanceId>.png", "PNG", "公式裁切图（环节②识别输入）"),
        ("records.jsonl", "UTF-8", "一 PDF 一行：instances[{instanceId,pageNo,bbox,bboxPixel,hasNumber,locateConfidence,crop,chapterTitle,contextText}] + instanceCount"),
        ("lineage_<uniqueId>.jsonl", "UTF-8", "逐 PDF keep（带 instances 计数）/ fail；跳过明细（页定位失败/坐标校验失败/裁切过小）"),
    ],
    "record_example": '{"docId":"formula_sample","fileName":"formula_sample.pdf","pageCount":2,"checksum":"<sha256>","instanceCount":3,"instances":[{"instanceId":"formula_sample-p1-f02","pageNo":1,"bbox":[288,305,890,365],"bboxPixel":[214,227,662,271],"hasNumber":true,"locateConfidence":0.95,"crop":"crops/formula_sample/formula_sample-p1-f02.png","chapterTitle":"第二章 公式","contextText":"其中 a、b 为已知常量，x 为自变量，c_i 为第 i 项系数……"}]}',
    "metrics": [
        ("离线单元测试", "5 / 5 通过", "定位+裁切+上下文抽取（中文字体 PDF）、单页定位失败跳过且整份 0 公式进失败清单、加密 PDF 失败、bbox 校验四种非法分支、空输入"),
        ("真实 API 冒烟", "3/3 定位准确", "3 个独立公式全部定位（含带编号 (2-3)）；行内提及的公式未被定位；章节标题「第二章 公式」与上下文正确"),
        ("grounding 坐标系", "bbox 0–1000 归一化", "与复杂版面线共用同一坐标系约定（Qwen3-VL 冒烟已验证）"),
    ],
    "latency": "单页定位约 10–20 s；2 页 PDF（1 页有公式）约 25 s",
    "needs_api": True,
    "deps": ["web", "llm", "pdf", "img"],
    "predict_example": '{"uniqueId":"fml001","isLastOperator":false}',
    "predict_note": "阶段首算子：不带 inputFile；环节② fml_formula_recognize 接续",
}

SPECS["fml_formula_recognize"] = {
    "name": "公式识别与结构化标注", "line": "公式文本", "stage": "环节② 公式识别 + 环节③ 结构化标注（产线末位）",
    "kind": "视觉大模型（一次调用五字段）+ 规则（LaTeX 语法校验）+ 文本大模型（修复 Prompt）",
    "role": "链路第 2 环（末位）：接 fml_formula_locate 产物；isLastOperator=true 收口",
    "input_desc": "上游 records.jsonl + crops/ 公式裁切图（inputFile 指向上游输出目录）",
    "output_desc": "records.jsonl（一个公式一行数据集）+ trace.jsonl（回溯字段）+ review.jsonl + 血缘 JSONL + 阶段 zip",
    "tech_stack": "Python 3.12、requests（VL 识别 + 文本修复）+ 正则规则解析器；HTTP 层 FastAPI + uvicorn。识别 Qwen/Qwen3-VL-8B-Instruct、修复 deepseek-ai/DeepSeek-V3.2",
    "definition": "交付说明环节②③ + §4.2/§4.3/§4.5 Prompt 原文：一次调用出 latex/symbols/context/双置信度（②③是逻辑环节不是两次调用）；LaTeX 语法校验是规则，失败走修复 Prompt",
    "boundary": "含义/单位为 null 不算失败（已确认口径 10）；回溯信息（页码/bbox/上下文范围）不进数据集（已确认口径 7）；修复只修语法不改内容；渲染回比不一致进复核由平台复核环节承担（B 修正的规则校验）",
    "scene": "公式文本产线终点：一个公式一行的数据集行（LaTeX + 符号表 + 上下文 + 双置信度）",
    "content_src": "LaTeX/符号/上下文由模型基于裁切图与页上下文生成；模型偶发把 null 写成字符串「null」，解析层归一为 null",
    "route": """```text
/predict（inputFile = 上游 fml_formula_locate 输出目录；isLastOperator=true）
   ↓  读 records.jsonl，展开成实例任务（一实例一次 VL 调用，并发 4–8）
每实例（裁切图长边压 1200px + §4.3 User：页号/bbox/章节标题/上下文 ≤2000 字）：
   ↓  §4.2 System（LaTeX 8 要求/符号与单位/上下文/双置信度/硬性约束）
   ↓  §4.6 校验：JSON 可解析且 latex 非空 → 否则重试 1 次；仍失败 → failed + review
   ↓  剥定界符（$、$$、\\[\\]、\\(\\)）；置信度截断 [0,0.98]
LaTeX 语法规则校验（check_latex）：
   ↓  空/花括号不配对或闭合先于开启/begin-end 环境不配对或未闭合/
   ↓  left-right 不配对/残留 $ → 非法
   ↓  非法 → §4.5 修复 Prompt（纯文本模式，DeepSeek-V3.2）：只修语法不改内容
   ↓    修复后复检通过 → 用修复值，复核记录「经修复 Prompt 修正」
   ↓    修复失败/复检仍非法 → 复核记录「语法非法（修复后仍失败）」，LaTeX 原值保留
复核分流（保留数据集行）：
   ↓  符号缺失或格式非法 / 定义位置无法定位（有符号但 definition 空）/
   ↓  置信度缺失或低于 0.8 / 语法修复未成功 → reviewStatus=待复核
数据集行（§五口径）：instanceId/latex/symbols/context/双置信度/状态
   ↓  页码/bbox/crop/章节标题/uncertain → trace.jsonl（不进数据集）
isLastOperator=true 收口阶段 zip
```""",
    "route_notes": [
        ("一次调用承载②③", "交付说明 §4.1：②③是逻辑环节不是两次模型调用——LaTeX/符号/上下文/双置信度一次 VL 调用齐出，语法校验与修复是规则与一次纯文本调用"),
        ("语法校验是规则不是模型", "交付说明已确认口径 4：花括号配对、begin/end 环境栈、left/right 配对、定界符残留四类确定性检查；修复 Prompt 明确「不增删符号、不改变上下标」"),
        ("「null」字符串归一", "实测 DeepSeek/VLM 偶发把 JSON null 输出成字符串 \"null\"；解析层统一归一为真 null（含义/单位为 null 合法的口径才能成立）"),
        ("修复链不静默吞错", "修复成功也进复核（reviewReason 标注「经修复」）——修复是机器动作，人需要知道哪些 LaTeX 被改过"),
    ],
    "params": [
        ("confidence_threshold", "Number", "否", "识别/语义阈值（两分数共用），默认 0.8（交付说明 §八任务级可调）"),
        ("concurrency", "Number", "否", "逐实例调用并发，默认 4，上限 8"),
    ],
    "upload_types": "`.jsonl` / `.zip`（链路中段，经 inputFile 接续）",
    "sample_dir": "dataset/sample/ = 上游真实产物（records.jsonl + crops/ 3 张裁切图 + pages/）",
    "sample_src": None, "sample_from": ("smoke_fml/locate_out", None),
    "outputs": [
        ("records.jsonl", "UTF-8", "一个公式一行：instanceId / latex（去定界符）/ symbols[{symbol,meaning,unit}] / context{chapter,number,definition} / recognitionConfidence / semanticConfidence / reviewStatus / revisionStatus"),
        ("trace.jsonl", "UTF-8", "回溯字段（不进数据集）：pageNo / bbox / crop / chapterTitle / uncertain"),
        ("review.jsonl", "UTF-8", "待复核行 + reviewReason（语法非法/经修复/符号缺失/定义无法定位/置信度低/识别失败）"),
        ("<run_id>_stage_output.zip", "zip", "isLastOperator=true 时整目录收口"),
    ],
    "record_example": '{"instanceId":"formula_sample-p1-f01","latex":"\\\\frac{a}{b} + \\\\sqrt{x} = \\\\sum_{i=1}^{n} c_i","symbols":[{"symbol":"a","meaning":"已知常量","unit":null},{"symbol":"c_i","meaning":"第 i 项系数","unit":null}],"context":{"chapter":"第二章 公式","number":null,"definition":"上文文本块说明了 a、b 为已知常量"},"recognitionConfidence":0.95,"semanticConfidence":0.92,"reviewStatus":"未进入复核","revisionStatus":"—"}',
    "metrics": [
        ("离线单元测试", "7 / 7 通过", "语法校验 8 分支（合法/空/括号/环境错配/未闭合/left-right/定界符）、修复链（修复成功标注/修复失败保留原值）、数据集行无回溯字段、模型失败分流、置信度 1.5 截断 0.98"),
        ("真实 API 冒烟", "3/3 LaTeX 正确", "frac+sqrt+sum、E=mc²、两行配方全部识别；符号含义与上下文定义取自页文本；语义置信 0.5 的实例正确进复核"),
        ("容错", "硅基流动 50507/超时不中断", "首轮链路遇服务端错误：实例进复核清单、其余实例照常完成；重跑 3/3 全过（.scratch/chain_fml.py）"),
    ],
    "latency": "单公式约 10–25 s（识别）+ 修复时加一次文本调用约 3–8 s；3 实例并发 4 约 60 s",
    "needs_api": True,
    "deps": ["web", "llm"],
    "predict_example": '{"inputFile":"<上游 outputFile>","isLastOperator":true}',
    "predict_note": "产线末位：isLastOperator=true 收口阶段 zip",
}

SPECS["img_region_locate"] = {
    "name": "图片区域定位与裁切", "line": "图文融合", "stage": "环节① 图片接入与判型",
    "kind": "CV/规则（不调模型）",
    "role": "阶段首算子：凭 uniqueId 取上传素材；输出供 img_type_classify 接续",
    "input_desc": "一个 zip 或散文件（JPG/PNG/BMP/WebP/TIFF，按文件名升序处理）",
    "output_desc": "regions/ 处理后图片 + records.jsonl（ImageRegion 登记）+ 血缘 JSONL",
    "tech_stack": "Python 3.12、Pillow（四角背景色基准 + 差分掩码 + 裁切）；HTTP 层 FastAPI + uvicorn。不调模型、不引入 OpenCV",
    "definition": "交付说明环节① #2：区域定位与裁切（CV/规则，不调模型）——实现口径：整图直通 + 拍照件黑边/白边自动裁剪",
    "boundary": "口径说明：交付说明未给出「区域」语义与原型（待确认 Q1），按整图直通 + 均色边框裁剪实现；重试 2 次仍失败跳过并记录（交付说明固定口径）。不做目标检测、不做主体分割",
    "scene": "图文融合产线第一环：图片可用性校验与内容区裁剪，登记 ImageRegion 供判型与描述消费",
    "content_src": "处理后图片来自上传图片的裁剪（无边框时原样直通）；不构造、不增强任何像素内容",
    "route": """```text
/uploadFile?uniqueId=<任务id_批次id> 上传 zip（阶段首算子）
   ↓  流式落盘 → 解压到 <INPUT_DIR>/<uniqueId>/
/predict（border_tolerance 默认 18；min_crop_size 默认 32）
逐图（文件名升序）：
   ↓  打开校验 + 四角采样均值作背景色基准
   ↓  差分掩码（|pixel-bg| > tolerance 视为内容）→ 内容区 bbox
   ↓  无均色边框 → bbox=整图 → 直通（不裁）；有边框 → 裁掉边框
   ↓  裁剪后任一边 <32px → 异常 → 重试（同参数，共 3 次机会）→ 仍失败跳过并记录
写 regions/<imageId>.png + records.jsonl（region 含像素 bbox/cropped/尺寸）
写 lineage（keep 带 cropped 与尺寸 / skip 带原因）
```""",
    "route_notes": [
        ("「区域定位」的实现口径（待确认 Q1）", "交付说明环节① #2 只写「CV/规则，不调模型」，未定义定位对象。默认按整图直通 + 均色边框（拍照黑边/扫描白边）裁剪实现；若甲方指其它语义（如主体检测），需原型或举例后替换本算子"),
        ("四角基准而非固定颜色", "拍照黑边、扫描白边、网页截图灰边颜色各异；取四角均值自适应判定背景，容差 18（0–255）排除 JPEG 噪声"),
        ("重试语义", "交付说明固定口径：区域定位重试 2 次（共 3 次机会）仍失败 → 跳过并记录「区域定位失败」；本实现纯确定性 CV，重试主要兜瞬时文件句柄/解码异常"),
    ],
    "params": [
        ("border_tolerance", "Number", "否", "边框判定容差（0–255），默认 18；差异低于容差视为背景"),
        ("min_crop_size", "Number", "否", "裁剪后最小保留边长（px），默认 32；过小判异常"),
    ],
    "upload_types": "`.jpg` / `.jpeg` / `.png` / `.bmp` / `.webp` / `.tif` / `.tiff` / `.zip`",
    "sample_dir": "dataset/sample/ = 5 张图（几何半圆、折线图、表格、流程示意、低分辨率三角形）",
    "sample_src": "img",
    "outputs": [
        ("regions/<imageId>.png", "PNG", "处理后图片（直通或裁边后，统一转 RGB PNG）"),
        ("records.jsonl", "UTF-8", "一图一行：imageId / fileName / image / region{bbox,cropped,width,height,sourceWidth,sourceHeight}"),
        ("lineage_<uniqueId>.jsonl", "UTF-8", "逐图 keep（带 cropped 与尺寸）/ skip（区域定位失败，含重试次数）"),
    ],
    "record_example": '{"imageId":"geometry_001","fileName":"geometry_001.png","image":"regions/geometry_001.png","region":{"bbox":[38,25,962,878],"cropped":true,"width":924,"height":853,"sourceWidth":1000,"sourceHeight":900}}',
    "metrics": [
        ("离线单元测试", "5 / 5 通过", "白底内容图直通不裁、黑边图精确裁出内容 bbox [60,50,340,250]、样本池 5 张全过、损坏图重试 3 次（计数断言）后跳过、参数校验"),
        ("真实样本", "5/5 通过", "matplotlib/PIL 生成的样本含均匀边缘被正确裁剪；裁剪输出图完整可开"),
        ("确定性", "同图两次处理字节一致", "纯 Pillow 确定性操作，不联网"),
    ],
    "latency": "5 张图全量 < 1 s（纯 CPU）；不依赖网络",
    "needs_api": False,
    "deps": ["web", "img"],
    "predict_example": '{"uniqueId":"img001","isLastOperator":false}',
    "predict_note": "阶段首算子：不带 inputFile；判型 img_type_classify 接续",
}

SPECS["img_type_classify"] = {
    "name": "图片判型", "line": "图文融合", "stage": "环节① 图片接入与判型",
    "kind": "视觉大模型（判型）",
    "role": "链路第 2 环：接 img_region_locate 产物；输出供 img_struct_describe 接续",
    "input_desc": "上游 records.jsonl + regions/ 图片；predict 必带参数 category（任务大类）",
    "output_desc": "records.jsonl（匹配图片，imageType 并入，图片随记录复制保持输出自包含）+ review.jsonl（低置信）+ 血缘 JSONL",
    "tech_stack": "Python 3.12、requests（VL 调用）+ ThreadPoolExecutor；HTTP 层 FastAPI + uvicorn。模型 Qwen/Qwen3-VL-8B-Instruct",
    "definition": "交付说明环节① #3#4 + §4.3.1 Prompt 原文：大类一致性校验（与任务所选比对，不一致跳过）+ 子类判定（match/子类/置信度/依据）",
    "boundary": "大类不一致（模型 match=false，或 category 与任务大类矛盾的规则兜底）→ 跳过该图记录「大类不一致」；判型置信度 <0.8 → 进复核（继续下游）；子类只能从给定列表选。不做要素提取与描述（环节②③职责）",
    "scene": "图文融合产线的分类闸：任务选了大类，只有匹配的图进要素提取与描述",
    "content_src": "判定结论由模型基于处理后图片生成；图片与上游记录原样透传（匹配图片复制进本算子输出，链路自包含）",
    "route": """```text
/predict（inputFile = 上游 img_region_locate 输出目录；category 必填）
   ↓  读 records.jsonl；逐图并发（4–8）
每图（§4.3.1 System 原文 + User「任务大类：{category}；这是第 N 张图片…」）：
   ↓  §4.3.0 公共约定并入 System（只述可见事实/uncertain/禁 1.0）
   ↓  输出校验：category 越枚举 / subtype 越枚举 / match 非布尔 → 重试 1 次
   ↓  置信度截断 [0,0.98]
路由：
   ↓  输出持续非法          → failed + review（不进下游）
   ↓  match=false           → 跳过清单（大类不一致（任务=X，实判=Y））
   ↓  match=true            → records.jsonl（imageType 并入），图片复制进输出
   ↓  置信度 <0.8           → 追加 review（判型置信度低于阈值），仍进下游
```""",
    "route_notes": [
        ("category 是任务参数", "交付说明环节① #3：大类一致性校验与任务所选比对——category（几何/统计/表格/示意）由平台按任务传入 predict，算子不猜"),
        ("跳过原因带双方大类", "跳过记录写明任务大类与实判大类（如「任务=几何，实判=统计」），复核/平台可直接消费"),
        ("输出自包含", "匹配图片复制进本算子输出目录（regions/ 同结构）——链路传输时下游 img_struct_describe 拿到的 inputFile 是本算子输出，取图不依赖上游目录"),
    ],
    "params": [
        ("category", "String", "是", "任务大类：几何 / 统计 / 表格 / 示意；缺失或非法 predict 整体报错（code=1）"),
        ("confidence_threshold", "Number", "否", "判型置信度阈值，默认 0.8；低于进复核不阻断"),
        ("concurrency", "Number", "否", "逐图调用并发，默认 4，上限 8"),
    ],
    "upload_types": "`.jsonl` / `.zip`（链路中段，经 inputFile 接续）",
    "sample_dir": "dataset/sample/ = 上游真实产物（records.jsonl + regions/ 5 张图）",
    "sample_src": None, "sample_from": ("smoke_img/loc_out", None),
    "outputs": [
        ("records.jsonl", "UTF-8", "匹配图片一图一行：上游字段 + imageType{match,category,subtype,confidence,reason,taskCategory}"),
        ("regions/", "PNG", "匹配图片副本（输出自包含，下游直接取图）"),
        ("review.jsonl", "UTF-8", "判型低置信/输出非法待复核 + reviewReason"),
        ("lineage_<run_id>.jsonl", "UTF-8", "逐图 keep（带 type_confidence）/ skip（大类不一致）/ fail"),
    ],
    "record_example": '{"imageId":"geometry_001",...,"imageType":{"match":true,"category":"几何","subtype":"平面几何图","confidence":0.95,"reason":"图中有半圆与标注点","taskCategory":"几何"}}',
    "metrics": [
        ("离线单元测试", "4 / 4 通过", "匹配保留/不一致跳过/低置信复核三分支、子类越枚举重试 1 次后失败、模型失败分流、category 必填校验"),
        ("真实 API 冒烟", "四类各一遍全对", "5 张图对 4 个任务大类分别判定：每类恰好匹配 1–2 张、其余 3–4 张大类不一致跳过且实判大类正确；子类全部在枚举内"),
        ("枚举兜底", "越枚举重试后失败不静默", "subtype 只从给定列表选（§4.3.1 规则），越枚举视为输出非法"),
    ],
    "latency": "单张判型约 8–15 s；5 张并发 4 约 20 s",
    "needs_api": True,
    "deps": ["web", "llm"],
    "predict_example": '{"inputFile":"<上游 outputFile>","category":"几何","isLastOperator":false}',
    "predict_note": "必带 category；链路中段经 inputFile 接续",
}

SPECS["img_struct_describe"] = {
    "name": "图文要素与描述生成", "line": "图文融合", "stage": "环节② 要素与结构提取 + 环节③ 描述生成（产线末位）",
    "kind": "视觉大模型（按判型选 4 套 Prompt 之一，一次调用）+ 规则回核",
    "role": "链路第 3 环（末位）：接 img_type_classify 产物；isLastOperator=true 收口",
    "input_desc": "上游 records.jsonl + regions/ 图片（含 imageType 判型结果）",
    "output_desc": "records.jsonl（一张一行数据集）+ details.jsonl（OCR/要素明细）+ review.jsonl + 血缘 JSONL + 阶段 zip",
    "tech_stack": "Python 3.12、requests（VL 调用）+ 正则回核；HTTP 层 FastAPI + uvicorn。模型 Qwen/Qwen3-VL-8B-Instruct",
    "definition": "交付说明环节②③ + §4.3.2–§4.3.5 四套大类 Prompt 原文（几何 4 字段/统计 6 字段/表格 4 字段/示意 6 字段）：一次调用同时返回要素（OCR/结构）与描述；回核字母数字来源；逐字段置信度",
    "boundary": "描述字段缺失/字段置信度缺失 → 进复核（§4.3.7）；数值缺失写 null 不估算；提取文字必须与 OCR 一致；不做证明推理（几何）、不猜色值（示意）。「无/不适用」是合法值",
    "scene": "图文融合产线终点：一张一行数据集（类型/子类/表格结构/字段化描述/三个置信度）",
    "content_src": "描述与 OCR 由模型基于处理后图片生成；回核校验描述中的数字必须在 OCR 文字中有依据",
    "route": """```text
/predict（inputFile = 上游 img_type_classify 输出目录；isLastOperator=true）
   ↓  读 records.jsonl；按 imageType.category 选 4 套 Prompt 之一
逐图并发（4–8，长边 1600px）：
   ↓  System = §4.3.0 公共约定 + 对应大类 Prompt 原文（§4.3.2–§4.3.5）
   ↓  输出校验：type/subtype 与判型一致 → 否则重试 1 次；持续非法 → failed + review
字段校验与规范化：
   ↓  描述缺字段 → 兜底「无」并记 problem；字段置信度缺失 → 记 problem
   ↓  全部置信度截断 [0,0.98]
   ↓  ocr_conf = OCR 块最低分；desc_conf = 描述字段最低分
回核（环节③ #2，规则）：
   ↓  描述文本中的数字逐一在 OCR 文字里找依据；
   ↓  无依据 → 「回核无依据内容：字段：数字」进复核
低置信计数（交付说明 §五）：
   ↓  判型/OCR/描述三个分数中低于阈值的个数（0–3）+ 原因串
数据集行（一张一行）：imageId/type/subtype/table(表格类)/description/
   confidence{type,ocr,desc}/lowConfidenceCount/lowConfidenceReasons/状态
   ↓  OCR 明细/结构要素（axis/legends/series/nodes/edges）/uncertain → details.jsonl
isLastOperator=true 收口阶段 zip
```""",
    "route_notes": [
        ("四套 Prompt 一次调用", "交付说明 §4.3.8：环节②+③由 Prompt 2/3/4/5 按判型结果选一，一次调用同时返回要素与描述——不做两阶段调用，判型结果（上游）决定选哪套"),
        ("回核规则", "交付说明环节③ #2：回核字母/数字来源。实现为描述文本数字在 OCR 文字中的存在性检查；实测统计图样本中模型写出的数据点 135 无 OCR 依据被正确标记进复核"),
        ("三个置信度并列", "判型（上游 imageType 透传）+ OCR 最低分 + 描述字段最低分，低于阈值个数计 lowConfidenceCount（§五字段），平台按 0–3 标红"),
        ("表格结构单列", "表格类的 rows/cols/headerRows/dataRows/merges 进数据集 table 字段（§五：非表格为空）；几何/统计/示意的结构要素（axis/legends/series/nodes/edges）进 details.jsonl 供复核查看"),
    ],
    "params": [
        ("confidence_threshold", "Number", "否", "低置信阈值（判型/OCR/描述三分共用），默认 0.8（任务级可调）"),
        ("concurrency", "Number", "否", "逐图调用并发，默认 4，上限 8"),
    ],
    "upload_types": "`.jsonl` / `.zip`（链路中段，经 inputFile 接续）",
    "sample_dir": "dataset/sample/ = 上游真实产物（records.jsonl + regions/，任务大类=几何：2 张图）",
    "sample_src": None, "sample_from": ("smoke_img/cls_out_几何", None),
    "outputs": [
        ("records.jsonl", "UTF-8", "一张一行：imageId / type / subtype / table（表格类或 null）/ description（按大类字段化）/ confidence{type,ocr,desc} / lowConfidenceCount / lowConfidenceReasons / reviewStatus"),
        ("details.jsonl", "UTF-8", "OCR 明细 / fieldConfidence / 结构要素（axis/legends/series/nodes/edges）/ uncertain（复核查看用）"),
        ("review.jsonl", "UTF-8", "待复核行 + reviewReason（缺字段/字段置信度缺失/回核无依据/三类低置信/生成失败）"),
        ("<run_id>_stage_output.zip", "zip", "isLastOperator=true 时整目录收口"),
    ],
    "record_example": '{"imageId":"table_001","type":"表格","subtype":"普通表格","table":{"rows":4,"cols":3,"headerRows":[["姓名","语文","数学"]],"dataRows":[["张三","92","88"]],"merges":[]},"description":{"表格类型":"普通表格","表头":"姓名、语文、数学","数据行":"张三 92 88；李四 85 95；王五 90 91","备注":"本表为学生成绩统计表"},"confidence":{"type":0.95,"ocr":0.98,"desc":0.95},"lowConfidenceCount":0,"lowConfidenceReasons":"","reviewStatus":"未进入复核","revisionStatus":"—"}',
    "metrics": [
        ("离线单元测试", "7 / 7 通过", "几何干净行、缺字段+缺字段置信度复核、回核无依据标记、表格 table 结构透传、subtype 不符重试 1 次后失败、判型低置信计数、缺输入报错"),
        ("真实 API 冒烟", "四类描述全对", "几何（半圆构成/辅助元素/位置关系）、统计（坐标轴/图例/逐点数据）、表格（表头/数据行）、示意（节点/连线/区域划分）字段齐全；统计图无依据数字 135 被回核正确标记"),
        ("端到端链路", ".scratch/chain_img.py 全通", "任务大类=几何：5 张进 2 跳 3（大类不一致），stage zip 一张一行 2 行"),
    ],
    "latency": "单张描述约 10–20 s（六字段输出较长）；2 张并发约 25 s",
    "needs_api": True,
    "deps": ["web", "llm"],
    "predict_example": '{"inputFile":"<上游 outputFile>","isLastOperator":true}',
    "predict_note": "产线末位：isLastOperator=true 收口阶段 zip",
}

# ---------------------------------------------------------------- 渲染：说明书

def _table(rows: list[tuple[str, str, str]], header: tuple[str, str, str] = ("分类", "字段", "值")) -> str:
    out = ["| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * len(header)) + " |"]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(out)


def render_manual(tag: str, s: dict) -> str:
    is_last = '"isLastOperator":true' in s["predict_example"]
    output_file_desc = (f"<OUTPUT_DIR>/<run_id>_stage_output.zip" if is_last
                        else f"<OUTPUT_DIR>/{tag}_<run_id>/")
    base_model = ""
    if s["needs_api"]:
        seg = s["tech_stack"].split("。")[-1]
        base_model = "外部大模型 API：" + seg.removeprefix("模型 ")
    else:
        base_model = "不涉及。无预训练权重、无本地推理；规则与确定性计算实现（纯标准库/PyMuPDF/Pillow）。"
    if "pdf" in s["deps"]:
        mem_note = "服务本体 + FastAPI 栈 < 200 MB；PDF 渲染峰值随页数与 DPI 线性（150 DPI A4 单页约 6 MB 位图）"
    elif "img" in s["deps"]:
        mem_note = "服务本体 + FastAPI 栈 < 200 MB；图片解码峰值按单图长边 1600 px 约 8 MB 位图估"
    else:
        mem_note = "服务本体 + FastAPI 栈 < 200 MB；纯文本处理，无媒体位图峰值"
    test_data_note = (
        f"包内自带（dataset/sample/）：{s['sample_dir']}；"
        + ("上游算子真实产物副本（链路冒烟实跑输出）。" if s.get("sample_from")
           else "由样本生成脚本确定性生成（_shared_tools/make_samples/）。")
        + "离线用例 mock 模型调用，联网冒烟用例直连真实 API")
    env_rows = [
        ("INPUT_DIR", "否", "runtime/input", "输入根（/uploadFile 往里解压；不设用包内默认）"),
        ("OUTPUT_DIR", "否", "runtime/output", "成果根；不设用包内默认"),
        ("PORT", "否", "6288", "服务监听端口（容器内统一 6288，宿主机由平台映射）"),
    ]
    if s["needs_api"]:
        env_rows += [
            ("SILICONFLOW_BASE_URL", "否", "https://api.siliconflow.cn/v1", "模型服务地址（已内置，可换私有网关）"),
            ("SILICONFLOW_API_KEY", "否", "<内置>", "模型密钥（已内置；生产建议环境变量注入覆盖）"),
        ]
    env_tbl = _table(env_rows, ("环境变量", "必填", "默认", "说明"))

    api_note = (
        "**依赖外部 API**：模型调用走硅基流动（OpenAI 兼容 chat/completions），"
        "统一约定 temperature 0、超时 60 s、传输层重试 2 次（最多 3 次）、JSON mode、"
        "置信度截断 [0, 0.98]、算子内并发 4–8。"
        if s["needs_api"]
        else "**不依赖外部 API**：纯规则实现，运行期无网络请求（测试依赖除外）。"
    )

    manual = f"""# 算子模型设计

## {s['name']}

### {s['name']}

#### {s['name']}

##### 基础信息

{_table([
    ("基础信息", "模型编号", f"`{tag}`（编号起区分作用，平台正式编号于交付前统一分配替换）"),
    ("基础信息", "模型名称", s["name"]),
    ("基础信息", "模型版本号", "v1.0.0"),
    ("基础信息", "所属产线", f"{s['line']} · {s['stage']}"),
    ("基础信息", "技术形态", s["kind"]),
    ("基础信息", "链路位置", s["role"]),
    ("基础信息", "输入类型", s["input_desc"]),
    ("基础信息", "输出类型", s["output_desc"]),
    ("基础信息", "技术栈", s["tech_stack"]),
    ("功能定义", "模型定义", s["definition"]),
    ("功能定义", "能力边界", s["boundary"]),
    ("功能定义", "适用场景", s["scene"]),
    ("输出内容描述", "内容来源", s["content_src"]),
    ("输出内容描述", "编码格式", "全部 JSONL/TXT 产物 UTF-8；图片 PNG；阶段收口 zip"),
    ("输出内容描述", "输出内容类型", "；".join(f"{n}（{d.split('，')[0]}）" for n, _, d in s["outputs"])),
])}

---

##### 技术方案

{s['route']}

""" + "\n\n".join(f"**{t}**：{d}" for t, d in s["route_notes"]) + f"""

---

##### 技术实现

{_table([
    ("训练方式", "不涉及。本算子无训练过程；阈值、枚举、Prompt 全文以集中显式常量实现（configs/config.py、configs/prompts.py），逐项可查、可审计"),
    ("基础模型", base_model),
    ("训练数据集", "不涉及。不使用任何训练语料"),
    ("测试数据集", test_data_note),
])}

**部署与运行**（完整验收步骤见 `{tag}-测试指令.md`）：

```bash
python -m pip install -r requirements.txt

INPUT_DIR=/data/input OUTPUT_DIR=/data/outputs \\
uvicorn inference:app --host 0.0.0.0 --port 6288
```

{env_tbl}

{api_note}

**复跑包内冒烟用例**（从交付包根运行）：

```bash
cd <交付包根>
python -m pytest {tag}/tests -q
```

---

##### 资源要求

| 项目 | 实测 / 说明 |
| --- | --- |
| 实测最小配置 · CPU | 单核可运行（受限并发为线程池，无进程并行） |
| 实测最小配置 · 内存 | {mem_note} |
| 实测最小配置 · 磁盘 | 镜像装载内容约 1 MB 级（inference.py + 内层包 + 样本）；单次运行产出见输出说明，成果只增不减由平台按 outputFile 管理 |
| 是否需要 GPU | 不需要。无本地权重；模型调用在远端 API |
| 实测数据规模 | 包内样本全量（{s['sample_dir'].split('：')[0]}），单请求完整跑通全部分支 |
| 是否依赖外部 API | {"是：硅基流动（SILICONFLOW_BASE_URL/SILICONFLOW_API_KEY 可覆盖）；调用约定见技术实现" if s["needs_api"] else "否：运行期无网络请求"} |
| 单次运行耗时 | {s['latency']} |
| 辅助模块依赖 | 运行必需：{', '.join(d for g in s['deps'] for d in DEPENDS[g] if g != 'test')}（与 requirements.txt 一致，版本锁定）；测试依赖：pytest==8.3.4 |

---

##### 训练后的模型性能指标

> 本算子无训练过程，不存在模型性能指标；下表为可复现的验证指标——全部由包内单元测试实际断言或真实 API 冒烟实跑得出，可用测试指令复现。

{_table([(m[0], m[1], m[2]) for m in s["metrics"]], ("指标", "数值", "说明"))}

##### 执行结果截图

| 项目 | 内容 |
| --- | --- |
| 执行结果截图 | [[执行结果截图:{s['name']}（{s['line']}）运行实录]] |

图 1　{s['name']}（{s['line']}）执行结果截图。

---

##### {s['name']}-输入示例

请求方式：`POST`（`/uploadFile` 上传素材、`/predict` 调用算子、`/removeFile` 幂等删除；`GET /healthz` 就绪探针）

`/uploadFile` 参数（三接口外壳各算子一致；是否为常规入口见「链路位置」）：

| 参数名称 | 描述 | 类型 | 是否必传 |
| --- | --- | --- | --- |
| uniqueId | 任务唯一标识（Query 参数），用作输入子目录名与血缘文件名 | String | 是 |
| file | 输入 zip 二进制流（流式落盘 ≤2GB；解压抹平层级；同一 uniqueId 重传先清空旧素材） | File | 是 |

`/predict` 参数（请求体 JSON）：

| 参数名称 | 描述 | 类型 | 是否必传 |
| --- | --- | --- | --- |
| uniqueId | 任务唯一标识（阶段首算子凭它取素材） | String | {('是' if 'uniqueId' in s['predict_example'] else '否')} |
| inputFile | 上游算子响应的 data.outputFile（链路中段必传；路径闸门校验） | String | {('否' if 'uniqueId' in s['predict_example'] else '是')} |
| isLastOperator | 是否阶段末算子（true 时输出收口 <run_id>_stage_output.zip） | Boolean | 否 |
""" + "\n".join(f"| {p} | {desc} | {typ} | {req} |" for p, typ, req, desc in
               ((pp[0], pp[1], pp[2], pp[3]) for pp in s["params"])) + f"""

{s['predict_note']}。请求示例：

```bash
curl -X POST http://127.0.0.1:6288/predict \\
  -H "Content-Type: application/json" \\
  -d '{s['predict_example']}'
```

输入内容版式：{s['upload_types']}。

---

##### {s['name']}-输出示例

结果写入输出目录 `<OUTPUT_DIR>/{tag}_<run_id>/`，`isLastOperator=true` 时整目录收口为 `<run_id>_stage_output.zip`：

| 文件 | 编码 | 说明 |
| --- | --- | --- |
""" + "\n".join(f"| `{n}` | {c} | {d} |" for n, c, d in s["outputs"]) + f"""

> 复核对接口径：""" + ("`review.jsonl` 每行在完整记录之外带 `reviewReason`（中文，供复核员阅读）与 `code`（小写下划线机器码，如 `low_confidence`、`model_call_failed`，供平台按类型生成复核单）；" if any("review" in n for n, _, _ in s["outputs"]) else "") + f"""`/predict` 响应 `data.skipped[]` / `data.failed[]` 条目同样带 `code`（如 `unsupported_suffix`、`pdf_encrypted`、`model_call_failed`）。同一行命中多个条件时只取优先级最高的一个码，无预设条件命中时为 `unclassified`。

`/predict` 成功响应（统一信封）：

```json
{{
  "code": 0,
  "msg": "success",
  "data": {{
    "outputFile": "{output_file_desc}",
    "lineageFile": "<OUTPUT_DIR>/{tag}_<run_id>/lineage_<run_id>.jsonl",
    "summary": {{...}},
    "skipped": [{{"name": "...", "reason": "...", "code": "unsupported_suffix"}}],
    "failed": [{{"name": "...", "reason": "...", "code": "model_call_failed"}}]
  }}
}}
```

主成果行示例（一行）：

```jsonl
{s['record_example']}
```
"""
    return manual


# ---------------------------------------------------------------- 渲染：测试指令

# 各算子的非法参数样例（用于测试指令负例 d；None 表示该算子无算子参数）
NEG_PARAM: dict[str, tuple[str, str] | None] = {
    "meta_clean_slice": None,
    "meta_genre_judge": ('"confidence_threshold":1.5', "confidence_threshold 须在 (0, 1) 之间"),
    "meta_fact_extract": ('"confidence_threshold":1.5', "confidence_threshold 须在 (0, 1) 之间"),
    "meta_field_fill": ('"confidence_threshold":1.5', "confidence_threshold 须在 (0, 1) 之间"),
    "lay_page_render": ('"dpi":999', "dpi 须在 72–300 之间"),
    "lay_page_detect": ('"confidence_threshold":1.5', "confidence_threshold 须在 (0, 1) 之间"),
    "fml_formula_locate": ('"dpi":999', "dpi 须在 72–300 之间"),
    "fml_formula_recognize": ('"confidence_threshold":1.5', "confidence_threshold 须在 (0, 1) 之间"),
    "img_region_locate": ('"border_tolerance":999', "border_tolerance 须在 0–255 之间"),
    "img_type_classify": ('"category":"风景"', "category 只能是 几何/统计/表格/示意"),
    "img_struct_describe": ('"confidence_threshold":1.5', "confidence_threshold 须在 (0, 1) 之间"),
}

UID = "smoke001"  # 测试指令统一任务标识


def render_testguide(tag: str, s: dict) -> str:
    stage_first = "uniqueId" in s["predict_example"]
    extra_env = " \\\n  SILICONFLOW_API_KEY=<密钥>" if s["needs_api"] else ""
    if stage_first:
        predict_body = re.sub(r'"uniqueId":"[^"]*"', f'"uniqueId":"{UID}"', s["predict_example"])
    else:
        predict_body = s["predict_example"]
    curl = 'curl -s -X POST http://127.0.0.1:6288/predict -H "Content-Type: application/json"'
    neg_rows = [
        ("a) predict 既无 uniqueId 也无 inputFile", f"{curl} -d '{{}}'"),
        ("b) inputFile 越界（路径闸门只放行 INPUT_DIR/OUTPUT_DIR 之内）",
         curl + " \\\n  -d '{\"inputFile\":\"C:/Windows/notepad.exe\"}'"),
        ("c) inputFile 在界内但不存在",
         curl + " \\\n  -d '{\"inputFile\":\"$WORK/outputs/no_such_dir\"}'"),
    ]
    neg_param = NEG_PARAM[tag]
    if neg_param:
        key = f'"uniqueId":"{UID}"' if stage_first else '"inputFile":"<上游 outputFile>"'
        neg_rows.append((f"d) 算子参数非法（{neg_param[1]}）",
                         curl + " \\\n  -d '{" + key + "," + neg_param[0] + "}'"))
    neg_block = "\n\n".join(f"# {t}\n{c}" for t, c in neg_rows)
    upload_step = f"""## 3. `POST /uploadFile`（阶段首算子上传形态）

```bash
# 打包样本（包内素材自足）
$PY - <<PY
import zipfile, pathlib
src = pathlib.Path("$TAG/dataset/sample")
with zipfile.ZipFile("$WORK/in.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(src.rglob("*")):
        if p.is_file():
            z.write(p, p.name)
print("ok")
PY

curl -s -X POST "http://127.0.0.1:6288/uploadFile?uniqueId={UID}" -F "file=@$WORK/in.zip"
```

期望：`code=0`；后缀不在白名单的条目被跳过并记录原因；同一 uniqueId 重传先清空旧素材。
""" if stage_first else f"""## 3. `POST /uploadFile`（本算子为链路中段）

正常形态经 `inputFile` 接续上游产物，不走 uploadFile。包内 `dataset/sample/` 预置了
上游真实产物，第 4 步直接以它作为 inputFile 喂入：

```bash
WORK_IN=$(cd "$TAG/dataset/sample" && pwd -W 2>/dev/null || cd "$TAG/dataset/sample" && pwd)
echo "upstream sample = $WORK_IN"
```
"""
    return f"""# {s['name']}（{s['line']}）测试指令

按顺序执行即可完成一次完整验收。命令按 Git Bash 写；换 Linux 容器把 `PY` 换成 `python3`。
{s['tech_stack'].split('。')[0]}{'；模型调用走硅基流动 API（需可出网）' if s['needs_api'] else '；不联网'}。

---

## 0. 前置准备

### 0.1 Python 与依赖

```bash
PY=/d/anaconda3/envs/use/python.exe
$PY -V    # 3.12
$PY -m pip install -r requirements.txt
```

### 0.2 工作目录与运行时目录

工作目录始终是交付包根（本文件所在目录）；临时文件放 `$WORK`（纯 ASCII 路径）。

```bash
cd <交付包根>
TAG={tag}
WORK=$($PY -c "import os,tempfile;p=os.path.join(tempfile.gettempdir(),'op{tag}');print(p.replace(os.sep,'/'))")
mkdir -p "$WORK/input" "$WORK/outputs"
```

---

## 1. 起服务

```bash
INPUT_DIR="$WORK/input" \\
OUTPUT_DIR="$WORK/outputs" \\
PYTHONIOENCODING=utf-8 \\
$PY -m uvicorn inference:app --host 0.0.0.0 --port 6288{extra_env}
```

---

## 2. `GET /healthz`

```bash
curl -s http://127.0.0.1:6288/healthz
```

期望：`code=0`、算子名与 map.json 一致。

---

{upload_step}
## 4. `POST /predict`

```bash
cat > "$WORK/predict.json" <<'JSON'
{predict_body}
JSON
curl -s -X POST http://127.0.0.1:6288/predict \\
  -H "Content-Type: application/json" --data-binary @"$WORK/predict.json"
```

{('uniqueId 已与第 3 步上传一致。' if stage_first else '把 `<上游 outputFile>` 替换为第 3 步的 $WORK_IN 路径。')}
期望：`code=0`；`data.summary` 计数与包内样本一致（分支覆盖见说明书「训练后的模型性能指标」）；
`data.skipped` / `data.failed` 给出中文原因与机器码 `code`。

{s['predict_note']}。

---

## 5. 产物校验

```bash
cd "$WORK/outputs" && ls
# 找到最新 {tag}_run_* 目录；isLastOperator=true 时为 <run_id>_stage_output.zip
head -n 2 "$WORK/outputs"/{tag}_run_*/records.jsonl    # 主成果前两行
head -n 3 "$WORK/outputs"/{tag}_run_*/lineage_*.jsonl  # 血缘首行 + 样本行
```

期望要点：

- 主成果一{('文档' if s['line'] == '文本元信息' else ('页' if s['line'] == '复杂版面' else ('公式' if s['line'] == '公式文本' else '张')))}一行，字段与交付说明数据集明细一致；
- 血缘首行 `record_type: task_lineage`，其后逐样本 `sample_lineage`{('；' if any('review' in n for n, _, _ in s['outputs']) else '。')}
""" + ("- `review.jsonl` 的行带中文 `reviewReason` 与机器码 `code`。" if any("review" in n for n, _, _ in s["outputs"]) else "") + f"""

---

## 6. `POST /removeFile`（幂等）

```bash
curl -s -X POST "http://127.0.0.1:6288/removeFile?uniqueId={UID}"
curl -s -X POST "http://127.0.0.1:6288/removeFile?uniqueId={UID}"   # 再删一次
```

期望：两次都 `code=0`（第二次 `deleted=false`），幂等。

---

## 7. 负例（各回 code=1 与中文原因，HTTP 仍 200）

```bash
{neg_block}
```

---

## 8. 复跑单元测试

```bash
cd <交付包根>
$PY -m pytest {tag}/tests -q
```

期望：全部通过（{s['metrics'][0][1]}；离线用例 mock 模型调用，不联网）。
"""


# ---------------------------------------------------------------- 渲染：requirements / Dockerfile

def render_requirements(s: dict) -> str:
    lines = [d for g in s["deps"] for d in DEPENDS[g]]
    lines.append("")
    lines.append("# 测试依赖（运行服务不需要）")
    lines.extend(DEPENDS["test"])
    return "\n".join(lines) + "\n"


def render_dockerfile(tag: str) -> str:
    return f"""FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY inference.py map.json ./
COPY {tag}/ ./{tag}/

ENV INPUT_DIR=/data/input OUTPUT_DIR=/data/outputs
RUN mkdir -p /data/input /data/outputs
EXPOSE 6288

CMD ["uvicorn", "inference:app", "--host", "0.0.0.0", "--port", "6288"]
"""


def render_inner_readme(tag: str, s: dict) -> str:
    deps = [d for g in s["deps"] for d in DEPENDS[g] if g != "test"]
    prompts_line = ("├── configs/prompts.py       Prompt 全文（凡调模型的算子）\n"
                    if s["needs_api"] else "")
    return f"""# {s['name']}（{s['line']}）

{s['stage']} · {s['kind']}。{s['role']}。

## 包结构

```text
{tag}/                       ← 本目录（算法实现）
├── operator.py              算子核心：run(input_dir, output_dir, params, log) -> dict
├── configs/config.py        阈值与枚举（集中可审计）
{prompts_line}├── utils/                   外壳与公共能力副本（vendor，包自包含）
├── dataset/sample/          样本（{s['sample_dir'].split('= ')[-1].split('（')[0].strip()}）
└── tests/                   离线单元测试（mock 模型调用，不联网）
```

包根（上一级）另有：`inference.py`（三接口外壳）、`map.json`（算子名）、`requirements.txt`
（版本锁定：{', '.join(d.split('==')[0] for d in deps)}）、`Dockerfile`、
`{tag}-算子说明书.md`、`{tag}-测试指令.md`。

## 快速运行

```bash
python -m pip install -r ../requirements.txt     # 在包根执行则去掉 ../
python -m uvicorn inference:app --host 0.0.0.0 --port 6288   # 在包根执行
python -m pytest {tag}/tests -q                  # 离线单测
```

完整验收步骤（healthz / uploadFile / predict / 负例 / 产物校验）见包根
`{tag}-测试指令.md`；技术方案与字段口径见 `{tag}-算子说明书.md`。
"""


# ---------------------------------------------------------------- 主流程

def copy_samples(tag: str, s: dict) -> None:
    dst = OPERATORS_ROOT / tag / tag / "dataset" / "sample"
    if dst.exists() and any(dst.iterdir()):
        return
    if s.get("sample_src"):
        src = SAMPLES / s["sample_src"]
        for f in sorted(src.iterdir()):
            shutil_copy(f, dst / f.name)
    elif s.get("sample_from"):
        src_root, only = s["sample_from"]
        src = SCRATCH / src_root
        for f in sorted(src.rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(src)
            if only and rel.name not in only and not any(str(rel).startswith(o) for o in only):
                continue
            shutil_copy(f, dst / rel)
    # 附一份说明
    note = dst.parent / "README.md"
    if not note.exists():
        note.write_text(
            f"# dataset/sample\n\n{s['sample_dir']}\n\n来源：samples_pool 生成脚本（_shared_tools/make_samples/）"
            + (" 或上游算子真实产物（.scratch 冒烟输出副本）" if s.get("sample_from") else "")
            + "。测试指令第 3/4 步直接消费本目录。\n", encoding="utf-8")


def shutil_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.is_file():
        return
    import shutil
    shutil.copy2(src, dst)


def main(argv: list[str]) -> None:
    tags = argv[1:] or list(SPECS)
    for tag in tags:
        s = SPECS[tag]
        root = OPERATORS_ROOT / tag
        (root / f"{tag}-算子说明书.md").write_text(render_manual(tag, s), encoding="utf-8")
        (root / f"{tag}-测试指令.md").write_text(render_testguide(tag, s), encoding="utf-8")
        (root / "requirements.txt").write_text(render_requirements(s), encoding="utf-8")
        (root / "Dockerfile").write_text(render_dockerfile(tag), encoding="utf-8")
        (root / tag / "README.md").write_text(render_inner_readme(tag, s), encoding="utf-8")
        copy_samples(tag, s)
        print(f"[ok] {tag}: 说明书 / 测试指令 / requirements / Dockerfile / README / sample")


if __name__ == "__main__":
    main(sys.argv)
