# 预训练文本产线算子（本组）

预训练文本数据清洗平台的算法算子仓库。**只做算法部分（规则型/小模型），不做前后端。**

> **本 work 目录为联调子集**：只从原仓库复制了正文提取组 5 个算子
> （`PTt_extract_html/xml/pdf/docx/doc_body`）。算子池启动时**自动发现**算子目录，
> 从原仓库复制新的 `PTt_xxx/` 目录进来即自动注册进池，无需改池代码；
> 只需在 `requirements-pool.txt` 启用对应依赖段（如有）。

- 需求真相源：`../【工具流程】预训练各模态产线工具分析-0927版.xlsx` 主表（文本V4）
- 开发规范：`docs/预训练文本算子开发规范-V1.0.md`（接口契约、响应外壳、参数、上限、指纹库、性能基线）
- 参考实现来源：`../pretrain_text_service_demo/`（旧契约 demo，仅迁移核心算法逻辑，接口层一律不用）

## 目录结构

```
pretrain_text/
├── common/                     # 共享层（每个算子镜像都打包）
│   ├── operator_base.py        #   处理器抽象（纯函数：记录进→结果出）、参数解析助手
│   ├── text_records.py         #   记录 I/O + 编码检测（charset-normalizer/chardet/GB18030 纠偏）
│   ├── auth_guard.py           #   认证拦截层（规范 3.4）：令牌摘要校验、/health 白名单、401/403
│   └── server.py               #   统一 HTTP 壳：/predict?detection=、/health、外壳、上限、降级服务
├── PTt_xxx/                    # 算子目录（目录名 = detection 值，规范 2.2）
│   ├── inference.py            #   薄入口：app = create_app(算子实例)
│   ├── model/network.py        #   核心逻辑类（继承 Operator，实现 process）
│   ├── configs/config.yaml     #   默认参数（与主表一致）、端口、上限
│   ├── dataset/sample/demo.jsonl
│   ├── tests/                  #   unittest（无外部依赖即可跑）
│   ├── map.json / requirements.txt / Dockerfile / README.md
└── docs/                       # 规范文档
```

## 接口契约（所有算子一致，详见规范第 3~6 章）

```
POST /predict?detection=PTt_xxx    multipart/form-data
  file: 待处理文件（jsonl 每行一条记录；html/xml/txt 整体一条）
  param_中文名: 算子行为参数（可选，中文原值）
  fingerprint_library/lexicon/dictionary/topic_table: 可选资源文件
→ 200 {code, msg, data:[{fieldName, tags, action, status, ...业务字段}]}
```

- `status` 为主表 U 列兼容字段：1=放行/处理成功，0=过滤/需复核（由 action 派生）
- 血缘归系统，算子不管；无状态，多副本安全；输入 ≤10MB、响应 ≤50MB，超限 413

## 新增算子步骤

1. 复制 `PTt_extract_html_body/` 为模板，目录名/detection 改为主表英文名
2. `model/network.py` 写核心逻辑（继承 `Operator`，实现 `process`，逐条处理用 `safe_map`）
3. `configs/config.yaml`、`map.json`、`README.md` 按算子填参数与业务字段（对照规范 5.3 / 4.4 表）
4. 写 `tests/` + `dataset/sample/demo.jsonl`，`python tests/test_network.py` 通过
5. 端口注册：在下方端口表登记（63xx 段，按主表 # 顺序分配）

## 端口注册表

| detection | 端口 | 状态 |
| --- | --- | --- |
| PTt_extract_html_body | 6301 | ✅ 批次1 完成（含 chrome 残留改进） |
| PTt_filter_anomalous_file | 6302 | ✅ 批次1 完成 |
| PTt_extract_xml_body | 6303 | ✅ 批次1 完成 |
| PTt_extract_pdf_body | 6304 | ✅ 批次1 完成（OCR 待接依赖） |
| PTt_extract_docx_body | 6305 | ✅ 批次1 完成 |
| PTt_extract_doc_body | 6306 | ✅ 批次1 完成（镜像装 LibreOffice） |
| PTt_extract_paper_body | 6307 | ✅ 批次1 完成 |
| PTt_remove_layout_noise | 6308 | ✅ 批次1 完成 |
| PTt_normalize_utf8_encoding | 6309 | ✅ 批次1 完成 |
| PTt_fix_mojibake | 6310 | ✅ 批次1 完成 |
| PTt_clean_web_noise | 6311 | ✅ 批次1 完成 |
| PTt_exact_hash_dedup | 6312 | ✅ 批次2 完成（指纹库增量回传+双格式兼容） |
| PTt_filter_length_anomaly | 6313 | ✅ 批次2 完成 |
| PTt_redact_pii | 6314 | ✅ 批次2 完成（含地址识别） |
| PTt_filter_sensitive_content | 6315 | ✅ 批次2 完成（甲方 BERT+词库双引擎；`param_识别引擎` 可切词库/模型） |
| PTt_chinese_tokenize | 6316 | ✅ 批次3 完成（jieba 词性族 n*/v*/a*） |
| PTt_clean_ner_en | 6317 | ✅ 批次3 完成（spaCy 主引擎+规则兜底，重做 demo 正则版） |
| PTt_normalize_format | 6318 | ✅ 批次3 完成（中文数字/日期/全半角/符号/停用词） |
| PTt_semantic_chunking | 6319 | ✅ 完成（章节/段落/标题策略+长度归一；embedding 升级位预留） |
| PTt_sliding_window_chunking | 6320 | ✅ 完成（窗口/步长/重叠/尾块策略） |
| PTt_build_qa_pairs | 6321 | ✅ 完成（仅组装不生成，对话式模板） |
| PTt_convert_mlm_format | 6322 | ✅ 完成（15%掩码+80/10/10，种子可复现；weight 自带词表，无 transformers 字符级降级） |
| PTt_build_nsp_pairs | 6323 | ✅ 完成（正负比例/随机·跨文档负采样） |
| PTt_generate_tokens | 6324 | ✅ 完成（BERT 词表自带+SHA256 快照；截断打标；需 transformers） |
| PTt_check_vocab_coverage | 6325 | ✅ 完成（内置 jieba-top5000 公开词典占位 + 上传覆盖；子串覆盖口径） |
| PTt_check_domain_relevance | 6326 | ✅ 完成（关键词口径；批级 relatedRatio + 逐条 hitKeywords） |
| PTt_check_length_distribution | 6327 | ✅ 完成（p50/p90+直方图；批级 lengthStats 进 extras） |
| PTt_check_topic_distribution | 6328 | ✅ 完成（zsy 主题表 30/114/279+16/47/209 内置；偏科不含"未匹配"；embedding 升级位） |
| PTt_filter_erroneous_text | 6329 | ⚠️ **临时版 v0.1.0**（规则错词引擎 39 词；Qwen3.5 评测通过后换引擎，外壳不变） |
| PTt_filter_semantic_anomaly | 6330 | ⚠️ **临时版 v0.1.0**（规则通顺度特征；Qwen logprob 接入位+阈值待校准） |
| PTt_measure_error_rate | 6331 | ⚠️ **临时版 v0.1.0**（与 #15 共用引擎；抽样可复现） |
| PTt_approx_dedup_large | 6332 | ⚠️ **临时版 v0.1.0**（单机 SimHash；百万级分布式待与平台定；指纹库兼容） |

## 回归基线（tests_assets/）

- 测试资产：`dirty_corpus_100`（101 个真实脏样本）+ `dirty_corpus`（17 个合成脏样本）+ `real_pages`（95 个真实网页，chinanews/cnblogs/eastmoney/segfault/pydocs/runoob）
- **HTML 提取噪声残留**：demo 基线 20.4% → 本仓库最终 **7.4%**（其中已核验大半为指标误报——"注册资本"等正文内容；真实 chrome 残留约 2%）。改进：密度区间内部导航/页脚词行剔除、"版权所有:站点名"署名行、"注册登录"组合词
- 全部 11 算子单测通过（`python PTt_xxx/tests/test_network.py`）

## 算子迁移/开发状态（28 个排产）

**已排除，不迁移不开发**（规范 1.3 / 11.5）：
- `PTt_filter_erroneous_text`（#15）、`PTt_filter_semantic_anomaly`（#16）、`PTt_measure_error_rate`（#32）——暂缓，选型待定；demo 实现为云端 LLM 调用，不可参考
- `PTt_approx_dedup_large`（#24）——暂缓；demo 亦无实现
- `PTt_check_duplicate_rate`——**不在主表算子清单内**（demo 多做的），不迁移
- #39 小范围预训练验证——不做（系统功能）
- demo 的接口层（uploadFile/predict JSON/lineage/workspace/云端模型网关）——旧契约，一律不用

**迁移批次**（规范第 10 章链路依赖）：

| 批次 | 算子 | 来源 |
| --- | --- | --- |
| 1 输入+提取+格式 | #2 异常过滤、#3 HTML✅、#4 XML、#5 PDF(补OCR)、#6 DOCX、#7 DOC、#8 论文、#9 版式噪声、#10 UTF-8、#11 乱码 | demo A 级改造（#10 直接用 common/text_records.py 检测逻辑） |
| 2 过滤+去重+脱敏 | #12 精确去重（新写+指纹库增量）、#13 网页噪声、#14 长度、#18 PII(补地址识别)、#17 敏感检测（壳，甲方模型） | demo 迁移 + 新写 |
| 3 分词+分片 | #19 中文分词、#21 格式规范化、#22 语义分块、#20 英文NER（**重做**，demo 只有正则）、#23 滑窗分块（新写） | 混合 |
| 4 样本构建+交付 | #25 QA、#26 MLM、#27 NSP（新写）、#37 Token序列（新写，BERT-base-Chinese） | 新写 |
| 5 质量评估 | #28 词汇覆盖（词典占位）、#29 领域相关、#30 长度分布、#31 主题打标（**重做**，demo 是 hash 近似） | demo 迁移 + 重做 |

## 本地验证

```bash
cd PTt_extract_html_body
python tests/test_network.py        # 单元测试（无需 FastAPI）
python inference.py --port 6301     # 开发模式起服务
curl -F "file=@dataset/sample/demo.jsonl" "http://localhost:6301/predict?detection=PTt_extract_html_body"
```

算子池开发模式（根目录）：

```bash
python inference.py --host 0.0.0.0 --port 17014   # 直接跑池 app，与 gunicorn 生产入口一致
curl http://localhost:17014/health
```

## 联调部署（算子池，对外 17014）

测试环境为整模态一个容器（规范 2.3 池化形态），池内算子启动时自动发现
（当前为正文提取组 5 个），经同一端点路由：

```bash
docker compose up -d                                  # 构建并启动（op-pretrain-text-pool:1.0.0）
curl http://localhost:17014/health                    # 列出全部可用 detection（白名单，无需令牌）
curl -H "X-Token: pretrain-text-pool-dev" \
     -F "file=@x.jsonl" \
     "http://localhost:17014/predict?detection=PTt_extract_html_body"   # 认证后调用
```

- 池化入口 `inference.py`（root），与单算子服务共用同一条 /predict 管线，后端无感知形态差异
- 镜像依赖按池内算子裁剪：当前 5 算子为纯规则，仅含壳依赖 + pypdf/python-docx +
  LibreOffice（#7 .doc 提取），无 torch/transformers（复制含模型算子时在
  `requirements-pool.txt` / `Dockerfile` 启用对应段落）
- compose 骨架沿用 demo，调整：端口 17014、去掉 workspace 卷（本池无状态）、gunicorn 多 worker

## 认证拦截（规范 3.4，会议纪要·平台认证拦截解决方案）

供给平台安全要求：容器对外接口必须鉴权，否则被安全扫描判定为漏洞。拦截层
`common/auth_guard.py` 由 `common/server.py` 在单算子/算子池两种形态统一安装
（含标准库降级服务），**一个模块保护全部算子，算子代码零改动**。

- **调用方**：请求头带 `X-Token: <令牌>`（兼容 `token` 头）；缺令牌 401、令牌
  不符 403；`/health` 白名单放行（K8s 探针）；`/docs` 等文档端点在认证启用时关闭
- **服务端配置**（环境变量，两种取一生效）：
  - `AUTH_TOKEN_SHA256`：令牌的 SHA-256 摘要（**生产推荐**，多调用方各持令牌时
    空格/逗号分隔多个摘要）。生成：
    `python -c "import hashlib;print(hashlib.sha256('你的令牌'.encode()).hexdigest())"`
  - `AUTH_TOKEN`：令牌明文（联调便利；摘要变量优先）
  - 两者都未设置时拦截关闭（本地开发/单测模式），启动日志会打 `[WARN]` 提醒
- **安全口径**：容器与环境变量只落摘要不落明文（"加密存储"）；比对用
  `secrets.compare_digest`（防时序侧信道）；不用 MD5（已不安全，SHA-256 同为
  摘要化口径）；令牌传输链路加密由网关/ingress TLS 承担（"加密传输"）
- **K8S 注入**：`kubectl create secret generic op-auth --from-literal=token=<令牌>`，
  容器 `AUTH_TOKEN` 经 `secretKeyRef` 引用
- 单测：`python common/test_auth_guard.py`（7 例，无需 FastAPI）
