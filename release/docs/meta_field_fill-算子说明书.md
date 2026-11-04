# 算子模型设计

## 元信息三组补全

### 元信息三组补全

#### 元信息三组补全

##### 基础信息

| 分类 | 字段 | 值 |
| --- | --- | --- |
| 基础信息 | 模型编号 | `meta_field_fill`（编号起区分作用，平台正式编号于交付前统一分配替换） |
| 基础信息 | 模型名称 | 元信息三组补全 |
| 基础信息 | 模型版本号 | v1.0.0 |
| 基础信息 | 所属产线 | 文本元信息 · 环节③ 元信息补全（产线末位） |
| 基础信息 | 技术形态 | 文本大模型（文档级一次补全 + 字段校验） |
| 基础信息 | 链路位置 | 链路第 4 环（末位）：接 meta_fact_extract 产物；isLastOperator=true 收口阶段 zip |
| 基础信息 | 输入类型 | 上游 records.jsonl（含 facts 事实清单） |
| 基础信息 | 输出类型 | records.jsonl（数据集行：16 字段 + 两个置信度 + 复核状态）+ fields_detail.jsonl（逐字段置信度明细）+ review.jsonl + 血缘 JSONL + 阶段 zip |
| 基础信息 | 技术栈 | Python 3.12、requests（JSON mode，max_tokens 8192）；HTTP 层 FastAPI + uvicorn。模型 deepseek-ai/DeepSeek-V3.2 |
| 功能定义 | 模型定义 | 交付说明环节③ + §4.3 Prompt 原文：三组 16 字段（结构化 4 + 基础 6 + 相关 6）逐字段置信度；结构化字段以事实清单为依据不得编造；没有的字段写「无/不适用」 |
| 功能定义 | 能力边界 | 补全按文档级一次完成（切片只用于读，交付说明已确认口径）；知识点少于 3 个按实际数量输出并在 uncertain 说明；价值观/历史/国家/宗教是正常数据集字段（已确认口径），不做特殊处理 |
| 功能定义 | 适用场景 | 文本元信息产线终点：一文档一行的数据集行，字段与交付说明 §五数据集明细一致 |
| 输出内容描述 | 内容来源 | 16 字段值由模型基于标题、正文（截断 6000 字）与事实清单生成；事实清单只作依据不改写 |
| 输出内容描述 | 编码格式 | 全部 JSONL/TXT 产物 UTF-8；图片 PNG；阶段收口 zip |
| 输出内容描述 | 输出内容类型 | records.jsonl（数据集行：docId + structured(4) + basic(6) + related(6) + extractConfidence + fillConfidence + reviewStatus + revisionStatus（对齐 §五样例））；fields_detail.jsonl（逐字段置信度 fieldConfidences + uncertain + problems（复核查看用）；review.jsonl（待复核行 + reviewReason（字段缺失/枚举非法/置信度输出失败/低于阈值））；<run_id>_stage_output.zip（isLastOperator=true 时整目录收口（阶段最终产物）） |

---

##### 技术方案

```text
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
```

**文档级一次补全**：交付说明环节③：切片只用于读，事实合并后文档级一次补全——避免逐片补全再投票的复杂度与不一致

**「无/不适用」是合法值**：交付说明 §4.3 规则 3：确实没有的字段写「无」或「不适用」，不要留空也不要硬编；校验层把缺失字段兜底为「无」而不是重试，就是这个口径的落地

**两个置信度并列**：抽取置信度（环节② facts.extractConfidence 透传）+ 补全置信度（本环节 16 字段最低分），对应数据集明细的两列（已确认口径 12）

---

##### 技术实现

| 分类 | 字段 | 值 |
| --- | --- | --- |
| 训练方式 | 不涉及。本算子无训练过程；阈值、枚举、Prompt 全文以集中显式常量实现（configs/config.py、configs/prompts.py），逐项可查、可审计 |
| 基础模型 | 外部大模型 API：deepseek-ai/DeepSeek-V3.2 |
| 训练数据集 | 不涉及。不使用任何训练语料 |
| 测试数据集 | 包内自带（dataset/sample/）：dataset/sample/ = 上游真实产物 records.jsonl（2 篇，含 facts）；上游算子真实产物副本（链路冒烟实跑输出）。离线用例 mock 模型调用，联网冒烟用例直连真实 API |

**部署与运行**（完整验收步骤见 `meta_field_fill-测试指令.md`）：

```bash
python -m pip install -r requirements.txt

INPUT_DIR=/data/input OUTPUT_DIR=/data/outputs \
uvicorn inference:app --host 0.0.0.0 --port 6288
```

| 环境变量 | 必填 | 默认 | 说明 |
| --- | --- | --- | --- |
| INPUT_DIR | 否 | runtime/input | 输入根（/uploadFile 往里解压；不设用包内默认） |
| OUTPUT_DIR | 否 | runtime/output | 成果根；不设用包内默认 |
| PORT | 否 | 6288 | 服务监听端口（容器内统一 6288，宿主机由平台映射） |
| SILICONFLOW_BASE_URL | 否 | https://api.siliconflow.cn/v1 | 模型服务地址（已内置，可换私有网关） |
| SILICONFLOW_API_KEY | 否 | <内置> | 模型密钥（已内置；生产建议环境变量注入覆盖） |

**依赖外部 API**：模型调用走硅基流动（OpenAI 兼容 chat/completions），统一约定 temperature 0、超时 60 s、传输层重试 2 次（最多 3 次）、JSON mode、置信度截断 [0, 0.98]、算子内并发 4–8。

**复跑包内冒烟用例**（从交付包根运行）：

```bash
cd <交付包根>
python -m pytest meta_field_fill/tests -q
```

---

##### 资源要求

| 项目 | 实测 / 说明 |
| --- | --- |
| 实测最小配置 · CPU | 单核可运行（受限并发为线程池，无进程并行） |
| 实测最小配置 · 内存 | 服务本体 + FastAPI 栈 < 200 MB；纯文本处理，无媒体位图峰值 |
| 实测最小配置 · 磁盘 | 镜像装载内容约 1 MB 级（inference.py + 内层包 + 样本）；单次运行产出见输出说明，成果只增不减由平台按 outputFile 管理 |
| 是否需要 GPU | 不需要。无本地权重；模型调用在远端 API |
| 实测数据规模 | 包内样本全量（dataset/sample/ = 上游真实产物 records.jsonl（2 篇，含 facts）），单请求完整跑通全部分支 |
| 是否依赖外部 API | 是：硅基流动（SILICONFLOW_BASE_URL/SILICONFLOW_API_KEY 可覆盖）；调用约定见技术实现 |
| 单次运行耗时 | 单篇一次调用约 5–25 s（16 字段输出较长）；2 篇并发约 30 s |
| 辅助模块依赖 | 运行必需：fastapi==0.116.1, uvicorn==0.51.0, python-multipart==0.0.32, starlette==0.47.3, pydantic==2.13.4, requests==2.34.2（与 requirements.txt 一致，版本锁定）；测试依赖：pytest==8.3.4 |

---

##### 训练后的模型性能指标

> 本算子无训练过程，不存在模型性能指标；下表为可复现的验证指标——全部由包内单元测试实际断言或真实 API 冒烟实跑得出，可用测试指令复现。

| 指标 | 数值 | 说明 |
| --- | --- | --- |
| 离线单元测试 | 4 / 4 通过 | 数据集行与 §五样例字段一致、缺字段兜底/枚举纠正/低置信复核、模型失败仅进失败清单、缺输入报错 |
| 真实 API 冒烟 | 两篇 16 字段齐全 | news_002 fillConfidence=0.8 未进复核；news_001 fillConfidence=0.7 正确进待复核；价值观/知识层次枚举值合法 |
| 端到端链路 | 5 HTML → 2 数据集行 | .scratch/chain_meta.py：uploadFile → predict×4 → stage zip 全通，数据集行字段齐全 |

##### 执行结果截图

| 项目 | 内容 |
| --- | --- |
| 执行结果截图 | [[执行结果截图:元信息三组补全（文本元信息）运行实录]] |

图 1　元信息三组补全（文本元信息）执行结果截图。

---

##### 元信息三组补全-输入示例

请求方式：`POST`（`/uploadFile` 上传素材、`/predict` 调用算子、`/removeFile` 幂等删除；`GET /healthz` 就绪探针）

`/uploadFile` 参数（三接口外壳各算子一致；是否为常规入口见「链路位置」）：

| 参数名称 | 描述 | 类型 | 是否必传 |
| --- | --- | --- | --- |
| uniqueId | 任务唯一标识（Query 参数），用作输入子目录名与血缘文件名 | String | 是 |
| file | 输入 zip 二进制流（流式落盘 ≤2GB；解压抹平层级；同一 uniqueId 重传先清空旧素材） | File | 是 |

`/predict` 参数（请求体 JSON）：

| 参数名称 | 描述 | 类型 | 是否必传 |
| --- | --- | --- | --- |
| uniqueId | 任务唯一标识（阶段首算子凭它取素材） | String | 否 |
| inputFile | 上游算子响应的 data.outputFile（链路中段必传；路径闸门校验） | String | 是 |
| isLastOperator | 是否阶段末算子（true 时输出收口 <run_id>_stage_output.zip） | Boolean | 否 |
| confidence_threshold | 补全质量阈值，默认 0.8（与抽取共用 0.80，任务级可调）；fillConfidence 低于进复核 | Number | 否 |
| max_text_chars | 送模型的正文最大字符，默认 6000（防超长上下文；须 ≥500） | Number | 否 |
| concurrency | 模型调用并发，默认 4，上限 8 | Number | 否 |

产线末位：isLastOperator=true，输出收口为阶段 zip。请求示例：

```bash
curl -X POST http://127.0.0.1:6288/predict \
  -H "Content-Type: application/json" \
  -d '{"inputFile":"<上游 outputFile>","isLastOperator":true}'
```

输入内容版式：`.jsonl` / `.zip`（链路中段，经 inputFile 接续）。

---

##### 元信息三组补全-输出示例

结果写入输出目录 `<OUTPUT_DIR>/meta_field_fill_<run_id>/`，`isLastOperator=true` 时整目录收口为 `<run_id>_stage_output.zip`：

| 文件 | 编码 | 说明 |
| --- | --- | --- |
| `records.jsonl` | UTF-8 | 数据集行：docId + structured(4) + basic(6) + related(6) + extractConfidence + fillConfidence + reviewStatus + revisionStatus（对齐 §五样例） |
| `fields_detail.jsonl` | UTF-8 | 逐字段置信度 fieldConfidences + uncertain + problems（复核查看用，不进数据集） |
| `review.jsonl` | UTF-8 | 待复核行 + reviewReason（字段缺失/枚举非法/置信度输出失败/低于阈值） |
| `<run_id>_stage_output.zip` | zip | isLastOperator=true 时整目录收口（阶段最终产物） |

> 复核对接口径：`review.jsonl` 每行在完整记录之外带 `reviewReason`（中文，供复核员阅读）与 `code`（小写下划线机器码，如 `low_confidence`、`model_call_failed`，供平台按类型生成复核单）；`/predict` 响应 `data.skipped[]` / `data.failed[]` 条目同样带 `code`（如 `unsupported_suffix`、`pdf_encrypted`、`model_call_failed`）。同一行命中多个条件时只取优先级最高的一个码，无预设条件命中时为 `unclassified`。

`/predict` 成功响应（统一信封）：

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "outputFile": "<OUTPUT_DIR>/<run_id>_stage_output.zip",
    "lineageFile": "<OUTPUT_DIR>/meta_field_fill_<run_id>/lineage_<run_id>.jsonl",
    "summary": {...},
    "skipped": [{"name": "...", "reason": "...", "code": "unsupported_suffix"}],
    "failed": [{"name": "...", "reason": "...", "code": "model_call_failed"}]
  }
}
```

主成果行示例（一行）：

```jsonl
{"docId":"news_002","structured":{"数据来源类型":"企业官网","可能的发布时间":"2026年7月3日","涉及人物、地点或组织":["某新能源科技公司","某农业大学","会展中心"],"时空变迁信息":"无"},"basic":{"知识层次":"技术应用","涉及的知识点列表":["战略合作","智能农机","地理标志产业","科研平台建设"],"主要一级行业":"制造业","行业场景":"新能源产业研发与人才引进","行业类型":"新能源","涉及的角色列表":["企业（新能源科技）","高校（农业大学）"]},"related":{"文章风格":"客观报道","内容类别":"企业动态","价值观":"褒","历史关联":"无关联","国家关联":"中国","宗教关联":"无"},"extractConfidence":0.95,"fillConfidence":0.8,"reviewStatus":"未进入复核","revisionStatus":"—"}
```
