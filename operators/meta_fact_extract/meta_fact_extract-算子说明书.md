# 算子模型设计

## 新闻事实抽取

### 新闻事实抽取

#### 新闻事实抽取

##### 基础信息

| 分类 | 字段 | 值 |
| --- | --- | --- |
| 基础信息 | 模型编号 | `meta_fact_extract`（编号起区分作用，平台正式编号于交付前统一分配替换） |
| 基础信息 | 模型名称 | 新闻事实抽取 |
| 基础信息 | 模型版本号 | v1.0.0 |
| 基础信息 | 所属产线 | 文本元信息 · 环节② 事实抽取 |
| 基础信息 | 技术形态 | 文本大模型（按片抽取 + 规则合并去重） |
| 基础信息 | 链路位置 | 链路第 3 环：接 meta_genre_judge 产物；输出供 meta_field_fill 接续 |
| 基础信息 | 输入类型 | 上游 records.jsonl（新闻文档，含 slices 与 genre） |
| 基础信息 | 输出类型 | records.jsonl（facts 字段并入）+ review.jsonl（来源缺失/冲突/低置信待复核）+ 血缘 JSONL |
| 基础信息 | 技术栈 | Python 3.12、requests（JSON mode）+ ThreadPoolExecutor；HTTP 层 FastAPI + uvicorn。模型 deepseek-ai/DeepSeek-V3.2 |
| 功能定义 | 模型定义 | 交付说明环节② + §4.2 Prompt 原文：抽取数据来源类型、发布时间候选、人物/地点/组织；时间保留原文粒度；同名实体分别列出；同字段多候选保留并标 conflict |
| 功能定义 | 能力边界 | 只抽文中明确出现的信息，不推断不补全；抽不到返回空数组不编造。冲突不阻断（进复核由人裁定）。切片只用于读；合并后交下游文档级补全 |
| 功能定义 | 适用场景 | 把新闻正文压成可审计的事实清单（来源/时间/实体），作为三组补全的依据，避免补全部编造 |
| 输出内容描述 | 内容来源 | 事实条目由模型基于上传正文生成，每条带原文短句与位置证据；正文原样透传 |
| 输出内容描述 | 编码格式 | 全部 JSONL/TXT 产物 UTF-8；图片 PNG；阶段收口 zip |
| 输出内容描述 | 输出内容类型 | records.jsonl（一文档一行：上游字段 + facts{sourceType,timeCandidates[],entities[],conflicts[],uncertain[],extractConfidence}）；review.jsonl（待复核文档 + reviewReason（来源类型缺失 / 候选冲突待裁定 / 抽取置信度低于阈值 / 全部切片失败））；lineage_<run_id>.jsonl（逐样本 keep（带 extract_confidence/entities/conflicts 计数）/ fail） |

---

##### 技术方案

```text
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
```

**为何按片抽再合并**：交付说明 §4.2：长文按切片分别抽取，合并时按 mention/时间值去重；单片上下文小、抽取稳定，合并交给确定性规则（可审计、可复现）

**冲突标记而非裁决**：交付说明环节②：时间候选冲突 → 标记，复核时裁定。算法侧不猜哪个对，把候选与理由摆给复核

**抽取置信度口径**：交付说明 §五：抽取置信度 = 来源/时间/实体最低分；任一类抽不到不计入最低分（空数组不拖垮整体）

---

##### 技术实现

| 分类 | 字段 | 值 |
| --- | --- | --- |
| 训练方式 | 不涉及。本算子无训练过程；阈值、枚举、Prompt 全文以集中显式常量实现（configs/config.py、configs/prompts.py），逐项可查、可审计 |
| 基础模型 | 外部大模型 API：deepseek-ai/DeepSeek-V3.2 |
| 训练数据集 | 不涉及。不使用任何训练语料 |
| 测试数据集 | 包内自带（dataset/sample/）：dataset/sample/ = 上游真实产物 records.jsonl（2 篇新闻，含 genre）；上游算子真实产物副本（链路冒烟实跑输出）。离线用例 mock 模型调用，联网冒烟用例直连真实 API |

**部署与运行**（完整验收步骤见 `meta_fact_extract-测试指令.md`）：

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
python -m pytest meta_fact_extract/tests -q
```

---

##### 资源要求

| 项目 | 实测 / 说明 |
| --- | --- |
| 实测最小配置 · CPU | 单核可运行（受限并发为线程池，无进程并行） |
| 实测最小配置 · 内存 | 服务本体 + FastAPI 栈 < 200 MB；纯文本处理，无媒体位图峰值 |
| 实测最小配置 · 磁盘 | 镜像装载内容约 1 MB 级（inference.py + 内层包 + 样本）；单次运行产出见输出说明，成果只增不减由平台按 outputFile 管理 |
| 是否需要 GPU | 不需要。无本地权重；模型调用在远端 API |
| 实测数据规模 | 包内样本全量（dataset/sample/ = 上游真实产物 records.jsonl（2 篇新闻，含 genre）），单请求完整跑通全部分支 |
| 是否依赖外部 API | 是：硅基流动（SILICONFLOW_BASE_URL/SILICONFLOW_API_KEY 可覆盖）；调用约定见技术实现 |
| 单次运行耗时 | 单片抽取约 3–8 s；2 篇（4 片）并发 4 约 15 s |
| 辅助模块依赖 | 运行必需：fastapi==0.116.1, uvicorn==0.51.0, python-multipart==0.0.32, starlette==0.47.3, pydantic==2.13.4, requests==2.34.2（与 requirements.txt 一致，版本锁定）；测试依赖：pytest==8.3.4 |

---

##### 训练后的模型性能指标

> 本算子无训练过程，不存在模型性能指标；下表为可复现的验证指标——全部由包内单元测试实际断言或真实 API 冒烟实跑得出，可用测试指令复现。

| 指标 | 数值 | 说明 |
| --- | --- | --- |
| 离线单元测试 | 6 / 6 通过 | 两片合并去重与 time conflict 标记、全部切片失败仅复核、来源缺失复核且继续、置信度 1.5 截断 0.98、单片解析失败重试 1 次且 uncertain 记录、缺输入报错 |
| 真实 API 冒烟 | 两篇抽取正确 | news_001 抽出 3 个时间候选（含开工/通车两个时间）并正确标 conflict、7 个实体分 person/place/org；news_002 单候选无冲突 |
| 抽取置信度 | 0.95 / 0.95 | 来源/时间/实体最低分口径与交付说明 §五一致 |

##### 执行结果截图

| 项目 | 内容 |
| --- | --- |
| 执行结果截图 | [[执行结果截图:新闻事实抽取（文本元信息）运行实录]] |

图 1　新闻事实抽取（文本元信息）执行结果截图。

---

##### 新闻事实抽取-输入示例

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
| confidence_threshold | 抽取质量阈值，默认 0.8（交付说明 §八：抽取/补全共用 0.80，任务级可调）；低于进复核 | Number | 否 |
| concurrency | 模型调用并发，默认 4，上限 8 | Number | 否 |

链路中段：inputFile 指向 meta_genre_judge 的 data.outputFile。请求示例：

```bash
curl -X POST http://127.0.0.1:6288/predict \
  -H "Content-Type: application/json" \
  -d '{"inputFile":"<上游 outputFile>","isLastOperator":false}'
```

输入内容版式：`.jsonl` / `.zip`（链路中段，经 inputFile 接续）。

---

##### 新闻事实抽取-输出示例

结果写入输出目录 `<OUTPUT_DIR>/meta_fact_extract_<run_id>/`，`isLastOperator=true` 时整目录收口为 `<run_id>_stage_output.zip`：

| 文件 | 编码 | 说明 |
| --- | --- | --- |
| `records.jsonl` | UTF-8 | 一文档一行：上游字段 + facts{sourceType,timeCandidates[],entities[],conflicts[],uncertain[],extractConfidence} |
| `review.jsonl` | UTF-8 | 待复核文档 + reviewReason（来源类型缺失 / 候选冲突待裁定 / 抽取置信度低于阈值 / 全部切片失败） |
| `lineage_<run_id>.jsonl` | UTF-8 | 逐样本 keep（带 extract_confidence/entities/conflicts 计数）/ fail |

> 复核对接口径：`review.jsonl` 每行在完整记录之外带 `reviewReason`（中文，供复核员阅读）与 `code`（小写下划线机器码，如 `low_confidence`、`model_call_failed`，供平台按类型生成复核单）；`/predict` 响应 `data.skipped[]` / `data.failed[]` 条目同样带 `code`（如 `unsupported_suffix`、`pdf_encrypted`、`model_call_failed`）。同一行命中多个条件时只取优先级最高的一个码，无预设条件命中时为 `unclassified`。

`/predict` 成功响应（统一信封）：

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "outputFile": "<OUTPUT_DIR>/meta_fact_extract_<run_id>/",
    "lineageFile": "<OUTPUT_DIR>/meta_fact_extract_<run_id>/lineage_<run_id>.jsonl",
    "summary": {...},
    "skipped": [{"name": "...", "reason": "...", "code": "unsupported_suffix"}],
    "failed": [{"name": "...", "reason": "...", "code": "model_call_failed"}]
  }
}
```

主成果行示例（一行）：

```jsonl
{"docId":"news_001",...,"facts":{"sourceType":{"value":"官方媒体","evidence":"来源：某市日报","confidence":0.95},"timeCandidates":[{"value":"2026年6月12日","granularity":"日","position":"第1段","confidence":0.98},{"value":"2021年3月","granularity":"月","position":"第3段","confidence":0.98}],"entities":[{"mention":"张伟","kind":"person","confidence":0.9}],"conflicts":[{"field":"time","candidates":["2026年6月12日","6月12日","2021年3月"],"reason":"多切片时间候选不一致"}],"uncertain":[],"extractConfidence":0.95}}
```
