# 算子模型设计

## 图文要素与描述生成

### 图文要素与描述生成

#### 图文要素与描述生成

##### 基础信息

| 分类 | 字段 | 值 |
| --- | --- | --- |
| 基础信息 | 模型编号 | `img_struct_describe`（编号起区分作用，平台正式编号于交付前统一分配替换） |
| 基础信息 | 模型名称 | 图文要素与描述生成 |
| 基础信息 | 模型版本号 | v1.0.0 |
| 基础信息 | 所属产线 | 图文融合 · 环节② 要素与结构提取 + 环节③ 描述生成（产线末位） |
| 基础信息 | 技术形态 | 视觉大模型（按判型选 4 套 Prompt 之一，一次调用）+ 规则回核 |
| 基础信息 | 链路位置 | 链路第 3 环（末位）：接 img_type_classify 产物；isLastOperator=true 收口 |
| 基础信息 | 输入类型 | 上游 records.jsonl + regions/ 图片（含 imageType 判型结果） |
| 基础信息 | 输出类型 | records.jsonl（一张一行数据集）+ details.jsonl（OCR/要素明细）+ review.jsonl + 血缘 JSONL + 阶段 zip |
| 基础信息 | 技术栈 | Python 3.12、requests（VL 调用）+ 正则回核；HTTP 层 FastAPI + uvicorn。模型 Qwen/Qwen3-VL-32B-Instruct |
| 功能定义 | 模型定义 | 交付说明环节②③ + §4.3.2–§4.3.5 四套大类 Prompt 原文（几何 4 字段/统计 6 字段/表格 4 字段/示意 6 字段）：一次调用同时返回要素（OCR/结构）与描述；回核字母数字来源；逐字段置信度 |
| 功能定义 | 能力边界 | 描述字段缺失/字段置信度缺失 → 进复核（§4.3.7）；数值缺失写 null 不估算；提取文字必须与 OCR 一致；不做证明推理（几何）、不猜色值（示意）。「无/不适用」是合法值 |
| 功能定义 | 适用场景 | 图文融合产线终点：一张一行数据集（类型/子类/表格结构/字段化描述/三个置信度） |
| 输出内容描述 | 内容来源 | 描述与 OCR 由模型基于处理后图片生成；回核校验描述中的数字必须在 OCR 文字中有依据 |
| 输出内容描述 | 编码格式 | 全部 JSONL/TXT 产物 UTF-8；图片 PNG；阶段收口 zip |
| 输出内容描述 | 输出内容类型 | records.jsonl（一张一行：imageId / type / subtype / table（表格类或 null）/ description（按大类字段化）/ confidence{type,ocr,desc} / lowConfidenceCount / lowConfidenceReasons / reviewStatus）；details.jsonl（OCR 明细 / fieldConfidence / 结构要素（axis/legends/series/nodes/edges）/ uncertain（复核查看用））；review.jsonl（待复核行 + reviewReason（缺字段/字段置信度缺失/回核无依据/三类低置信/生成失败））；<run_id>_stage_output.zip（isLastOperator=true 时整目录收口） |

---

##### 技术方案

```text
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
```

**四套 Prompt 一次调用**：交付说明 §4.3.8：环节②+③由 Prompt 2/3/4/5 按判型结果选一，一次调用同时返回要素与描述——不做两阶段调用，判型结果（上游）决定选哪套

**回核规则**：交付说明环节③ #2：回核字母/数字来源。实现为描述文本数字在 OCR 文字中的存在性检查；实测统计图样本中模型写出的数据点 135 无 OCR 依据被正确标记进复核

**三个置信度并列**：判型（上游 imageType 透传）+ OCR 最低分 + 描述字段最低分，低于阈值个数计 lowConfidenceCount（§五字段），平台按 0–3 标红

**表格结构单列**：表格类的 rows/cols/headerRows/dataRows/merges 进数据集 table 字段（§五：非表格为空）；几何/统计/示意的结构要素（axis/legends/series/nodes/edges）进 details.jsonl 供复核查看

---

##### 技术实现

| 分类 | 字段 | 值 |
| --- | --- | --- |
| 训练方式 | 不涉及。本算子无训练过程；阈值、枚举、Prompt 全文以集中显式常量实现（configs/config.py、configs/prompts.py），逐项可查、可审计 |
| 基础模型 | 外部大模型 API：Qwen/Qwen3-VL-32B-Instruct |
| 训练数据集 | 不涉及。不使用任何训练语料 |
| 测试数据集 | 包内自带（dataset/sample/）：dataset/sample/ = 上游真实产物（records.jsonl + regions/，任务大类=几何：2 张图）；上游算子真实产物副本（链路冒烟实跑输出）。离线用例 mock 模型调用，联网冒烟用例直连真实 API |

**部署与运行**（完整验收步骤见 `img_struct_describe-测试指令.md`）：

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
python -m pytest img_struct_describe/tests -q
```

---

##### 资源要求

| 项目 | 实测 / 说明 |
| --- | --- |
| 实测最小配置 · CPU | 单核可运行（受限并发为线程池，无进程并行） |
| 实测最小配置 · 内存 | 服务本体 + FastAPI 栈 < 200 MB；纯文本处理，无媒体位图峰值 |
| 实测最小配置 · 磁盘 | 镜像装载内容约 1 MB 级（inference.py + 内层包 + 样本）；单次运行产出见输出说明，成果只增不减由平台按 outputFile 管理 |
| 是否需要 GPU | 不需要。无本地权重；模型调用在远端 API |
| 实测数据规模 | 包内样本全量（dataset/sample/ = 上游真实产物（records.jsonl + regions/，任务大类=几何），单请求完整跑通全部分支 |
| 是否依赖外部 API | 是：硅基流动（SILICONFLOW_BASE_URL/SILICONFLOW_API_KEY 可覆盖）；调用约定见技术实现 |
| 单次运行耗时 | 单张描述约 10–20 s（六字段输出较长）；2 张并发约 25 s |
| 辅助模块依赖 | 运行必需：fastapi==0.116.1, uvicorn==0.51.0, python-multipart==0.0.32, starlette==0.47.3, pydantic==2.13.4, requests==2.34.2（与 requirements.txt 一致，版本锁定）；测试依赖：pytest==8.3.4 |

---

##### 训练后的模型性能指标

> 本算子无训练过程，不存在模型性能指标；下表为可复现的验证指标——全部由包内单元测试实际断言或真实 API 冒烟实跑得出，可用测试指令复现。

| 指标 | 数值 | 说明 |
| --- | --- | --- |
| 离线单元测试 | 7 / 7 通过 | 几何干净行、缺字段+缺字段置信度复核、回核无依据标记、表格 table 结构透传、subtype 不符重试 1 次后失败、判型低置信计数、缺输入报错 |
| 真实 API 冒烟 | 四类描述全对 | 几何（半圆构成/辅助元素/位置关系）、统计（坐标轴/图例/逐点数据）、表格（表头/数据行）、示意（节点/连线/区域划分）字段齐全；统计图无依据数字 135 被回核正确标记 |
| 端到端链路 | .scratch/chain_img.py 全通 | 任务大类=几何：5 张进 2 跳 3（大类不一致），stage zip 一张一行 2 行 |

##### 执行结果截图

| 项目 | 内容 |
| --- | --- |
| 执行结果截图 | [[执行结果截图:图文要素与描述生成（图文融合）运行实录]] |

图 1　图文要素与描述生成（图文融合）执行结果截图。

---

##### 图文要素与描述生成-输入示例

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
| confidence_threshold | 低置信阈值（判型/OCR/描述三分共用），默认 0.8（任务级可调） | Number | 否 |
| concurrency | 逐图调用并发，默认 4，上限 8 | Number | 否 |

产线末位：isLastOperator=true 收口阶段 zip。请求示例：

```bash
curl -X POST http://127.0.0.1:6288/predict \
  -H "Content-Type: application/json" \
  -d '{"inputFile":"<上游 outputFile>","isLastOperator":true}'
```

输入内容版式：`.jsonl` / `.zip`（链路中段，经 inputFile 接续）。

---

##### 图文要素与描述生成-输出示例

结果写入输出目录 `<OUTPUT_DIR>/img_struct_describe_<run_id>/`，`isLastOperator=true` 时整目录收口为 `<run_id>_stage_output.zip`：

| 文件 | 编码 | 说明 |
| --- | --- | --- |
| `records.jsonl` | UTF-8 | 一张一行：imageId / type / subtype / table（表格类或 null）/ description（按大类字段化）/ confidence{type,ocr,desc} / lowConfidenceCount / lowConfidenceReasons / reviewStatus |
| `details.jsonl` | UTF-8 | OCR 明细 / fieldConfidence / 结构要素（axis/legends/series/nodes/edges）/ uncertain（复核查看用） |
| `review.jsonl` | UTF-8 | 待复核行 + reviewReason（缺字段/字段置信度缺失/回核无依据/三类低置信/生成失败） |
| `<run_id>_stage_output.zip` | zip | isLastOperator=true 时整目录收口 |

> 复核对接口径：`review.jsonl` 每行在完整记录之外带 `reviewReason`（中文，供复核员阅读）与 `code`（小写下划线机器码，如 `low_confidence`、`model_call_failed`，供平台按类型生成复核单）；`/predict` 响应 `data.skipped[]` / `data.failed[]` 条目同样带 `code`（如 `unsupported_suffix`、`pdf_encrypted`、`model_call_failed`）。同一行命中多个条件时只取优先级最高的一个码，无预设条件命中时为 `unclassified`。

`/predict` 成功响应（统一信封）：

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "outputFile": "<OUTPUT_DIR>/<run_id>_stage_output.zip",
    "lineageFile": "<OUTPUT_DIR>/img_struct_describe_<run_id>/lineage_<run_id>.jsonl",
    "summary": {...},
    "skipped": [{"name": "...", "reason": "...", "code": "unsupported_suffix"}],
    "failed": [{"name": "...", "reason": "...", "code": "model_call_failed"}]
  }
}
```

主成果行示例（一行）：

```jsonl
{"imageId":"table_001","type":"表格","subtype":"普通表格","table":{"rows":4,"cols":3,"headerRows":[["姓名","语文","数学"]],"dataRows":[["张三","92","88"]],"merges":[]},"description":{"表格类型":"普通表格","表头":"姓名、语文、数学","数据行":"张三 92 88；李四 85 95；王五 90 91","备注":"本表为学生成绩统计表"},"confidence":{"type":0.95,"ocr":0.98,"desc":0.95},"lowConfidenceCount":0,"lowConfidenceReasons":"","reviewStatus":"未进入复核","revisionStatus":"—"}
```
