# 算子模型设计

## 新闻体裁判定

### 新闻体裁判定

#### 新闻体裁判定

##### 基础信息

| 分类 | 字段 | 值 |
| --- | --- | --- |
| 基础信息 | 模型编号 | `meta_genre_judge`（编号起区分作用，平台正式编号于交付前统一分配替换） |
| 基础信息 | 模型名称 | 新闻体裁判定 |
| 基础信息 | 模型版本号 | v1.0.0 |
| 基础信息 | 所属产线 | 文本元信息 · 环节① 文档接入与切片 |
| 基础信息 | 技术形态 | 文本大模型（规则粗筛 + 大模型边界判定） |
| 基础信息 | 链路位置 | 链路第 2 环：接 meta_clean_slice 产物（inputFile）；输出供 meta_fact_extract 接续 |
| 基础信息 | 输入类型 | 上游 records.jsonl（一文档一行，含 slices）；或打包该文件的 zip |
| 基础信息 | 输出类型 | records.jsonl（新闻文档，genre 字段并入）+ review.jsonl（低置信/解析失败待复核）+ 血缘 JSONL |
| 基础信息 | 技术栈 | Python 3.12、requests（OpenAI 兼容 chat/completions，JSON mode）+ ThreadPoolExecutor 受限并发；HTTP 层 FastAPI + uvicorn。模型 deepseek-ai/DeepSeek-V3.2（硅基流动） |
| 功能定义 | 模型定义 | 交付说明环节① #3 + §4.1 Prompt 原文：四条标准（事件性/时效性/事实性/公共传播性）同时满足才算新闻；输出 is_news / category / 四条件 / 置信度 / 依据 |
| 功能定义 | 能力边界 | 规则粗筛只过滤明显非新闻（教程类标题、广告关键词），边界情形全部交给模型；置信度 <0.8 一律进复核（不论是否新闻）；≥0.8 且非新闻才跳过。不做实体抽取、不做时间抽取（环节②职责） |
| 功能定义 | 适用场景 | 文本元信息产线的总闸：非新闻文档在此出局，只有新闻进事实抽取与三组补全 |
| 输出内容描述 | 内容来源 | 判定结论由模型基于上传正文生成；正文本身原样透传给下游，本算子不改正文 |
| 输出内容描述 | 编码格式 | 全部 JSONL/TXT 产物 UTF-8；图片 PNG；阶段收口 zip |
| 输出内容描述 | 输出内容类型 | records.jsonl（新闻文档一文档一行：上游字段 + genre{is_news,category,conditions,confidence,reason,evidence,screening}）；review.jsonl（待复核文档：完整记录 + reviewReason（置信度低于阈值 / 模型输出解析失败））；lineage_<run_id>.jsonl（首行 task_lineage；其后逐样本 keep（带 genre_confidence）/ skip / review） |

---

##### 技术方案

```text
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
```

**为什么规则粗筛在前**：教程、广告两类在高置信下模型也能判对，但纯规则即可零成本出局；粗筛关键词刻意收窄（只过滤「明显非新闻」），避免误杀边界文档——误杀代价高于多花一次模型调用

**复核口径**：交付说明 §4.1：置信度 <0.8 → 进复核（不论是否新闻）——所以低置信的疑似广告也进复核而不是直接跳过，由人工裁定

**category 枚举**：消息/通讯/特写/专访/通报/评论/广告/教程/通知/其他；模型越枚举时兜底「其他」并保留原值进 reason，不因枚举违规重试（判定结论本身可用）

---

##### 技术实现

| 分类 | 字段 | 值 |
| --- | --- | --- |
| 训练方式 | 不涉及。本算子无训练过程；阈值、枚举、Prompt 全文以集中显式常量实现（configs/config.py、configs/prompts.py），逐项可查、可审计 |
| 基础模型 | 外部大模型 API：deepseek-ai/DeepSeek-V3.2（硅基流动） |
| 训练数据集 | 不涉及。不使用任何训练语料 |
| 测试数据集 | 包内自带（dataset/sample/）：dataset/sample/ = 上游真实产物 records.jsonl（4 篇：2 新闻 + 广告 + 教程）；上游算子真实产物副本（链路冒烟实跑输出）。离线用例 mock 模型调用，联网冒烟用例直连真实 API |

**部署与运行**（完整验收步骤见 `meta_genre_judge-测试指令.md`）：

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
python -m pytest meta_genre_judge/tests -q
```

---

##### 资源要求

| 项目 | 实测 / 说明 |
| --- | --- |
| 实测最小配置 · CPU | 单核可运行（受限并发为线程池，无进程并行） |
| 实测最小配置 · 内存 | 服务本体 + FastAPI 栈 < 200 MB；纯文本处理，无媒体位图峰值 |
| 实测最小配置 · 磁盘 | 镜像装载内容约 1 MB 级（inference.py + 内层包 + 样本）；单次运行产出见输出说明，成果只增不减由平台按 outputFile 管理 |
| 是否需要 GPU | 不需要。无本地权重；模型调用在远端 API |
| 实测数据规模 | 包内样本全量（dataset/sample/ = 上游真实产物 records.jsonl（4 篇），单请求完整跑通全部分支 |
| 是否依赖外部 API | 是：硅基流动（SILICONFLOW_BASE_URL/SILICONFLOW_API_KEY 可覆盖）；调用约定见技术实现 |
| 单次运行耗时 | 单篇判定约 3–8 s（DeepSeek-V3.2）；并发 4 时 4 篇约 10 s |
| 辅助模块依赖 | 运行必需：fastapi==0.116.1, uvicorn==0.51.0, python-multipart==0.0.32, starlette==0.47.3, pydantic==2.13.4, requests==2.34.2（与 requirements.txt 一致，版本锁定）；测试依赖：pytest==8.3.4 |

---

##### 训练后的模型性能指标

> 本算子无训练过程，不存在模型性能指标；下表为可复现的验证指标——全部由包内单元测试实际断言或真实 API 冒烟实跑得出，可用测试指令复现。

| 指标 | 数值 | 说明 |
| --- | --- | --- |
| 离线单元测试 | 4 / 4 通过 | 规则粗筛命中不调模型（monkeypatch 断言）、新闻保留/非新闻跳过/低置信复核三分路由、解析失败进复核、缺输入报错 |
| 真实 API 冒烟 | 2 新闻判定正确（消息，0.98/0.95） | 广告页与教程页被规则粗筛直接跳过（零模型调用）；分类、四条件、依据句齐全 |
| 重试口径 | 传输 429/5xx 重试 2 次；JSON 解析失败重试 1 次 | 公共 llm_client 统一实现（.scratch/verify_shared_client.py 验证） |

##### 执行结果截图

| 项目 | 内容 |
| --- | --- |
| 执行结果截图 | [[执行结果截图:新闻体裁判定（文本元信息）运行实录]] |

图 1　新闻体裁判定（文本元信息）执行结果截图。

---

##### 新闻体裁判定-输入示例

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
| confidence_threshold | 体裁判定置信度阈值，默认 0.8（交付说明 §八：固定 0.8，此处仅为任务级预留）；低于阈值进复核 | Number | 否 |
| concurrency | 模型调用并发，默认 4，上限 8（交付说明 §八：并发数 4–8） | Number | 否 |

链路中段：inputFile 指向上游 meta_clean_slice 响应的 data.outputFile。请求示例：

```bash
curl -X POST http://127.0.0.1:6288/predict \
  -H "Content-Type: application/json" \
  -d '{"inputFile":"<上游 outputFile>","isLastOperator":false}'
```

输入内容版式：`.jsonl` / `.zip`（本算子为链路中段，正常形态经 inputFile 接续，不走 uploadFile）。

---

##### 新闻体裁判定-输出示例

结果写入输出目录 `<OUTPUT_DIR>/meta_genre_judge_<run_id>/`，`isLastOperator=true` 时整目录收口为 `<run_id>_stage_output.zip`：

| 文件 | 编码 | 说明 |
| --- | --- | --- |
| `records.jsonl` | UTF-8 | 新闻文档一文档一行：上游字段 + genre{is_news,category,conditions,confidence,reason,evidence,screening} |
| `review.jsonl` | UTF-8 | 待复核文档：完整记录 + reviewReason（置信度低于阈值 / 模型输出解析失败） |
| `lineage_<run_id>.jsonl` | UTF-8 | 首行 task_lineage；其后逐样本 keep（带 genre_confidence）/ skip / review |

> 复核对接口径：`review.jsonl` 每行在完整记录之外带 `reviewReason`（中文，供复核员阅读）与 `code`（小写下划线机器码，如 `low_confidence`、`model_call_failed`，供平台按类型生成复核单）；`/predict` 响应 `data.skipped[]` / `data.failed[]` 条目同样带 `code`（如 `unsupported_suffix`、`pdf_encrypted`、`model_call_failed`）。同一行命中多个条件时只取优先级最高的一个码，无预设条件命中时为 `unclassified`。

`/predict` 成功响应（统一信封）：

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "outputFile": "<OUTPUT_DIR>/meta_genre_judge_<run_id>/",
    "lineageFile": "<OUTPUT_DIR>/meta_genre_judge_<run_id>/lineage_<run_id>.jsonl",
    "summary": {...},
    "skipped": [{"name": "...", "reason": "...", "code": "unsupported_suffix"}],
    "failed": [{"name": "...", "reason": "...", "code": "model_call_failed"}]
  }
}
```

主成果行示例（一行）：

```jsonl
{"docId":"news_001",...,"genre":{"is_news":true,"category":"消息","conditions":{"event":true,"timeliness":true,"factual":true,"public":true},"confidence":0.98,"reason":"主体+事件+时间+地点齐备","evidence":["6月12日某市地铁3号线通车"],"screening":"model"}}
```
