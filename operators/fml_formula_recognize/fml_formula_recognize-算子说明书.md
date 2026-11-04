# 算子模型设计

## 公式识别与结构化标注

### 公式识别与结构化标注

#### 公式识别与结构化标注

##### 基础信息

| 分类 | 字段 | 值 |
| --- | --- | --- |
| 基础信息 | 模型编号 | `fml_formula_recognize`（编号起区分作用，平台正式编号于交付前统一分配替换） |
| 基础信息 | 模型名称 | 公式识别与结构化标注 |
| 基础信息 | 模型版本号 | v1.0.0 |
| 基础信息 | 所属产线 | 公式文本 · 环节② 公式识别 + 环节③ 结构化标注（产线末位） |
| 基础信息 | 技术形态 | 视觉大模型（一次调用五字段）+ 规则（LaTeX 语法校验）+ 文本大模型（修复 Prompt） |
| 基础信息 | 链路位置 | 链路第 2 环（末位）：接 fml_formula_locate 产物；isLastOperator=true 收口 |
| 基础信息 | 输入类型 | 上游 records.jsonl + crops/ 公式裁切图（inputFile 指向上游输出目录） |
| 基础信息 | 输出类型 | records.jsonl（一个公式一行数据集）+ trace.jsonl（回溯字段）+ review.jsonl + 血缘 JSONL + 阶段 zip |
| 基础信息 | 技术栈 | Python 3.12、requests（VL 识别 + 文本修复）+ 正则规则解析器；HTTP 层 FastAPI + uvicorn。识别 Qwen/Qwen3-VL-32B-Instruct、修复 deepseek-ai/DeepSeek-V3.2 |
| 功能定义 | 模型定义 | 交付说明环节②③ + §4.2/§4.3/§4.5 Prompt 原文：一次调用出 latex/symbols/context/双置信度（②③是逻辑环节不是两次调用）；LaTeX 语法校验是规则，失败走修复 Prompt |
| 功能定义 | 能力边界 | 含义/单位为 null 不算失败（已确认口径 10）；回溯信息（页码/bbox/上下文范围）不进数据集（已确认口径 7）；修复只修语法不改内容；渲染回比不一致进复核由平台复核环节承担（B 修正的规则校验） |
| 功能定义 | 适用场景 | 公式文本产线终点：一个公式一行的数据集行（LaTeX + 符号表 + 上下文 + 双置信度） |
| 输出内容描述 | 内容来源 | LaTeX/符号/上下文由模型基于裁切图与页上下文生成；模型偶发把 null 写成字符串「null」，解析层归一为 null |
| 输出内容描述 | 编码格式 | 全部 JSONL/TXT 产物 UTF-8；图片 PNG；阶段收口 zip |
| 输出内容描述 | 输出内容类型 | records.jsonl（一个公式一行：instanceId / latex（去定界符）/ symbols[{symbol,meaning,unit}] / context{chapter,number,definition} / recognitionConfidence / semanticConfidence / reviewStatus / revisionStatus）；trace.jsonl（回溯字段（不进数据集）：pageNo / bbox / crop / chapterTitle / uncertain）；review.jsonl（待复核行 + reviewReason（语法非法/经修复/符号缺失/定义无法定位/置信度低/识别失败））；<run_id>_stage_output.zip（isLastOperator=true 时整目录收口） |

---

##### 技术方案

```text
/predict（inputFile = 上游 fml_formula_locate 输出目录；isLastOperator=true）
   ↓  读 records.jsonl，展开成实例任务（一实例一次 VL 调用，并发 4–8）
每实例（裁切图长边压 1200px + §4.3 User：页号/bbox/章节标题/上下文 ≤2000 字）：
   ↓  §4.2 System（LaTeX 8 要求/符号与单位/上下文/双置信度/硬性约束）
   ↓  §4.6 校验：JSON 可解析且 latex 非空 → 否则重试 1 次；仍失败 → failed + review
   ↓  剥定界符（$、$$、\[\]、\(\)）；置信度截断 [0,0.98]
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
```

**一次调用承载②③**：交付说明 §4.1：②③是逻辑环节不是两次模型调用——LaTeX/符号/上下文/双置信度一次 VL 调用齐出，语法校验与修复是规则与一次纯文本调用

**语法校验是规则不是模型**：交付说明已确认口径 4：花括号配对、begin/end 环境栈、left/right 配对、定界符残留四类确定性检查；修复 Prompt 明确「不增删符号、不改变上下标」

**「null」字符串归一**：实测 DeepSeek/VLM 偶发把 JSON null 输出成字符串 "null"；解析层统一归一为真 null（含义/单位为 null 合法的口径才能成立）

**修复链不静默吞错**：修复成功也进复核（reviewReason 标注「经修复」）——修复是机器动作，人需要知道哪些 LaTeX 被改过

---

##### 技术实现

| 分类 | 字段 | 值 |
| --- | --- | --- |
| 训练方式 | 不涉及。本算子无训练过程；阈值、枚举、Prompt 全文以集中显式常量实现（configs/config.py、configs/prompts.py），逐项可查、可审计 |
| 基础模型 | 外部大模型 API：识别 Qwen/Qwen3-VL-32B-Instruct、修复 deepseek-ai/DeepSeek-V3.2 |
| 训练数据集 | 不涉及。不使用任何训练语料 |
| 测试数据集 | 包内自带（dataset/sample/）：dataset/sample/ = 上游真实产物（records.jsonl + crops/ 3 张裁切图 + pages/）；上游算子真实产物副本（链路冒烟实跑输出）。离线用例 mock 模型调用，联网冒烟用例直连真实 API |

**部署与运行**（完整验收步骤见 `fml_formula_recognize-测试指令.md`）：

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
python -m pytest fml_formula_recognize/tests -q
```

---

##### 资源要求

| 项目 | 实测 / 说明 |
| --- | --- |
| 实测最小配置 · CPU | 单核可运行（受限并发为线程池，无进程并行） |
| 实测最小配置 · 内存 | 服务本体 + FastAPI 栈 < 200 MB；纯文本处理，无媒体位图峰值 |
| 实测最小配置 · 磁盘 | 镜像装载内容约 1 MB 级（inference.py + 内层包 + 样本）；单次运行产出见输出说明，成果只增不减由平台按 outputFile 管理 |
| 是否需要 GPU | 不需要。无本地权重；模型调用在远端 API |
| 实测数据规模 | 包内样本全量（dataset/sample/ = 上游真实产物（records.jsonl + crops/ 3 张裁切图 + pages/）），单请求完整跑通全部分支 |
| 是否依赖外部 API | 是：硅基流动（SILICONFLOW_BASE_URL/SILICONFLOW_API_KEY 可覆盖）；调用约定见技术实现 |
| 单次运行耗时 | 单公式约 10–25 s（识别）+ 修复时加一次文本调用约 3–8 s；3 实例并发 4 约 60 s |
| 辅助模块依赖 | 运行必需：fastapi==0.116.1, uvicorn==0.51.0, python-multipart==0.0.32, starlette==0.47.3, pydantic==2.13.4, requests==2.34.2（与 requirements.txt 一致，版本锁定）；测试依赖：pytest==8.3.4 |

---

##### 训练后的模型性能指标

> 本算子无训练过程，不存在模型性能指标；下表为可复现的验证指标——全部由包内单元测试实际断言或真实 API 冒烟实跑得出，可用测试指令复现。

| 指标 | 数值 | 说明 |
| --- | --- | --- |
| 离线单元测试 | 7 / 7 通过 | 语法校验 8 分支（合法/空/括号/环境错配/未闭合/left-right/定界符）、修复链（修复成功标注/修复失败保留原值）、数据集行无回溯字段、模型失败分流、置信度 1.5 截断 0.98 |
| 真实 API 冒烟 | 3/3 LaTeX 正确 | frac+sqrt+sum、E=mc²、两行配方全部识别；符号含义与上下文定义取自页文本；语义置信 0.5 的实例正确进复核 |
| 容错 | 硅基流动 50507/超时不中断 | 首轮链路遇服务端错误：实例进复核清单、其余实例照常完成；重跑 3/3 全过（.scratch/chain_fml.py） |

##### 执行结果截图

| 项目 | 内容 |
| --- | --- |
| 执行结果截图 | [[执行结果截图:公式识别与结构化标注（公式文本）运行实录]] |

图 1　公式识别与结构化标注（公式文本）执行结果截图。

---

##### 公式识别与结构化标注-输入示例

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
| confidence_threshold | 识别/语义阈值（两分数共用），默认 0.8（交付说明 §八任务级可调） | Number | 否 |
| concurrency | 逐实例调用并发，默认 4，上限 8 | Number | 否 |

产线末位：isLastOperator=true 收口阶段 zip。请求示例：

```bash
curl -X POST http://127.0.0.1:6288/predict \
  -H "Content-Type: application/json" \
  -d '{"inputFile":"<上游 outputFile>","isLastOperator":true}'
```

输入内容版式：`.jsonl` / `.zip`（链路中段，经 inputFile 接续）。

---

##### 公式识别与结构化标注-输出示例

结果写入输出目录 `<OUTPUT_DIR>/fml_formula_recognize_<run_id>/`，`isLastOperator=true` 时整目录收口为 `<run_id>_stage_output.zip`：

| 文件 | 编码 | 说明 |
| --- | --- | --- |
| `records.jsonl` | UTF-8 | 一个公式一行：instanceId / latex（去定界符）/ symbols[{symbol,meaning,unit}] / context{chapter,number,definition} / recognitionConfidence / semanticConfidence / reviewStatus / revisionStatus |
| `trace.jsonl` | UTF-8 | 回溯字段（不进数据集）：pageNo / bbox / crop / chapterTitle / uncertain |
| `review.jsonl` | UTF-8 | 待复核行 + reviewReason（语法非法/经修复/符号缺失/定义无法定位/置信度低/识别失败） |
| `<run_id>_stage_output.zip` | zip | isLastOperator=true 时整目录收口 |

> 复核对接口径：`review.jsonl` 每行在完整记录之外带 `reviewReason`（中文，供复核员阅读）与 `code`（小写下划线机器码，如 `low_confidence`、`model_call_failed`，供平台按类型生成复核单）；`/predict` 响应 `data.skipped[]` / `data.failed[]` 条目同样带 `code`（如 `unsupported_suffix`、`pdf_encrypted`、`model_call_failed`）。同一行命中多个条件时只取优先级最高的一个码，无预设条件命中时为 `unclassified`。

`/predict` 成功响应（统一信封）：

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "outputFile": "<OUTPUT_DIR>/<run_id>_stage_output.zip",
    "lineageFile": "<OUTPUT_DIR>/fml_formula_recognize_<run_id>/lineage_<run_id>.jsonl",
    "summary": {...},
    "skipped": [{"name": "...", "reason": "...", "code": "unsupported_suffix"}],
    "failed": [{"name": "...", "reason": "...", "code": "model_call_failed"}]
  }
}
```

主成果行示例（一行）：

```jsonl
{"instanceId":"formula_sample-p1-f01","latex":"\\frac{a}{b} + \\sqrt{x} = \\sum_{i=1}^{n} c_i","symbols":[{"symbol":"a","meaning":"已知常量","unit":null},{"symbol":"c_i","meaning":"第 i 项系数","unit":null}],"context":{"chapter":"第二章 公式","number":null,"definition":"上文文本块说明了 a、b 为已知常量"},"recognitionConfidence":0.95,"semanticConfidence":0.92,"reviewStatus":"未进入复核","revisionStatus":"—"}
```
