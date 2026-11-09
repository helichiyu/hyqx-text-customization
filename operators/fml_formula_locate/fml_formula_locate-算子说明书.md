# 算子模型设计

## 公式区域定位与裁切

### 公式区域定位与裁切

#### 公式区域定位与裁切

##### 基础信息

| 分类 | 字段 | 值 |
| --- | --- | --- |
| 基础信息 | 模型编号 | `fml_formula_locate`（编号起区分作用，平台正式编号于交付前统一分配替换） |
| 基础信息 | 模型名称 | 公式区域定位与裁切 |
| 基础信息 | 模型版本号 | v1.0.0 |
| 基础信息 | 所属产线 | 公式文本 · 环节① 素材接入与定位 |
| 基础信息 | 技术形态 | 规则（PDF 渲染）+ 视觉大模型（grounding 定位） |
| 基础信息 | 链路位置 | 阶段首算子：凭 uniqueId 取上传素材；输出供 fml_formula_recognize 接续 |
| 基础信息 | 输入类型 | 一个 zip 或散文件（PDF：混合文档，含正文与公式） |
| 基础信息 | 输出类型 | crops/ 公式裁切图 + pages/ 页图 + records.jsonl（FormulaInstance 登记）+ 血缘 JSONL |
| 基础信息 | 技术栈 | Python 3.12、PyMuPDF（渲染 + 页文本块）+ Pillow（裁切）+ requests（VL grounding）；HTTP 层 FastAPI + uvicorn。模型 Qwen/Qwen3-VL-8B-Instruct |
| 功能定义 | 模型定义 | 交付说明环节① #1–#3：接收校验素材 → 定位混合文档中的公式区域（只处理独立成行或带编号的公式，行内公式不处理）→ 裁切并登记可回溯公式实例（页码、bbox、上下文文本范围） |
| 功能定义 | 能力边界 | 定位 Prompt 由本侧按环节①职责自行设计（交付说明只给识别 Prompt §4.2）；单页定位失败跳过该页并记录；裁切/坐标校验失败跳过该实例并记录；整份 0 公式按交付说明进失败清单（任务待处理口径） |
| 功能定义 | 适用场景 | 公式文本产线第一环：从混合 PDF 里把独立公式连图带上下文摘出来，登记成可回溯实例 |
| 输出内容描述 | 内容来源 | 裁切图与上下文文本全部来自上传 PDF；bbox/hasNumber/置信度由模型基于页图判定 |
| 输出内容描述 | 编码格式 | 全部 JSONL/TXT 产物 UTF-8；图片 PNG；阶段收口 zip |
| 输出内容描述 | 输出内容类型 | pages/<docId>/*.png（逐页渲染图（定位与裁切的底图））；crops/<docId>/<instanceId>.png（公式裁切图（环节②识别输入））；records.jsonl（一 PDF 一行：instances[{instanceId,pageNo,bbox,bboxPixel,hasNumber,locateConfidence,crop,chapterTitle,contextText}] + instanceCount）；lineage_<uniqueId>.jsonl（逐 PDF keep（带 instances 计数）/ fail；跳过明细（页定位失败/坐标校验失败/裁切过小）） |

---

##### 技术方案

```text
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
```

**定位 Prompt 自行设计的口径**：交付说明 §四只给识别 Prompt；定位按环节①职责（只处理独立成行或带编号的公式）设计 System，输出仅 bbox/hasNumber/置信度，不做识别

**行内公式不处理**：交付说明环节①范围注：Prompt 明确「行内公式（嵌在句子里的符号）不要定位」，实测样本中行内提及的公式未被定位，独立 3 个公式全部定位

**上下文 ≤2000 字**：交付说明 §4.3：contextText 取公式前后各 1–2 段，总长 ≤2000 字；实现取与公式纵向最近文本块向前后各扩至多 2 段、超长截断

**回溯字段口径**：页码/bbox/上下文范围只用于内部回溯（环节②消费），最终数据集不展示（§五）——本算子产物保留全部回溯字段，裁剪发生在 fml_formula_recognize

---

##### 技术实现

| 分类 | 字段 | 值 |
| --- | --- | --- |
| 训练方式 | 不涉及。本算子无训练过程；阈值、枚举、Prompt 全文以集中显式常量实现（configs/config.py、configs/prompts.py），逐项可查、可审计 |
| 基础模型 | 外部大模型 API：Qwen/Qwen3-VL-8B-Instruct |
| 训练数据集 | 不涉及。不使用任何训练语料 |
| 测试数据集 | 包内自带（dataset/sample/）：dataset/sample/ = formula_sample.pdf（第二章：无编号分式+根式、带编号 E=mc²(2-3)、两行配方、行内提及不处理、第 2 页无公式）；由样本生成脚本确定性生成（_shared_tools/make_samples/）。离线用例 mock 模型调用，联网冒烟用例直连真实 API |

**部署与运行**（完整验收步骤见 `fml_formula_locate-测试指令.md`）：

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
python -m pytest fml_formula_locate/tests -q
```

---

##### 资源要求

| 项目 | 实测 / 说明 |
| --- | --- |
| 实测最小配置 · CPU | 单核可运行（受限并发为线程池，无进程并行） |
| 实测最小配置 · 内存 | 服务本体 + FastAPI 栈 < 200 MB；PDF 渲染峰值随页数与 DPI 线性（150 DPI A4 单页约 6 MB 位图） |
| 实测最小配置 · 磁盘 | 镜像装载内容约 1 MB 级（inference.py + 内层包 + 样本）；单次运行产出见输出说明，成果只增不减由平台按 outputFile 管理 |
| 是否需要 GPU | 不需要。无本地权重；模型调用在远端 API |
| 实测数据规模 | 包内样本全量（dataset/sample/ = formula_sample.pdf（第二章），单请求完整跑通全部分支 |
| 是否依赖外部 API | 是：硅基流动（SILICONFLOW_BASE_URL/SILICONFLOW_API_KEY 可覆盖）；调用约定见技术实现 |
| 单次运行耗时 | 单页定位约 10–20 s；2 页 PDF（1 页有公式）约 25 s |
| 辅助模块依赖 | 运行必需：fastapi==0.116.1, uvicorn==0.51.0, python-multipart==0.0.32, starlette==0.47.3, pydantic==2.13.4, requests==2.34.2, pymupdf==1.28.2, pillow==12.0.0（与 requirements.txt 一致，版本锁定）；测试依赖：pytest==8.3.4 |

---

##### 训练后的模型性能指标

> 本算子无训练过程，不存在模型性能指标；下表为可复现的验证指标——全部由包内单元测试实际断言或真实 API 冒烟实跑得出，可用测试指令复现。

| 指标 | 数值 | 说明 |
| --- | --- | --- |
| 离线单元测试 | 5 / 5 通过 | 定位+裁切+上下文抽取（中文字体 PDF）、单页定位失败跳过且整份 0 公式进失败清单、加密 PDF 失败、bbox 校验四种非法分支、空输入 |
| 真实 API 冒烟 | 3/3 定位准确 | 3 个独立公式全部定位（含带编号 (2-3)）；行内提及的公式未被定位；章节标题「第二章 公式」与上下文正确 |
| grounding 坐标系 | bbox 0–1000 归一化 | 与复杂版面线共用同一坐标系约定（Qwen3-VL 冒烟已验证） |

##### 执行结果截图

| 项目 | 内容 |
| --- | --- |
| 执行结果截图 | [[执行结果截图:公式区域定位与裁切（公式文本）运行实录]] |

图 1　公式区域定位与裁切（公式文本）执行结果截图。

---

##### 公式区域定位与裁切-输入示例

请求方式：`POST`（`/uploadFile` 上传素材、`/predict` 调用算子、`/removeFile` 幂等删除；`GET /healthz` 就绪探针）

`/uploadFile` 参数（三接口外壳各算子一致；是否为常规入口见「链路位置」）：

| 参数名称 | 描述 | 类型 | 是否必传 |
| --- | --- | --- | --- |
| uniqueId | 任务唯一标识（Query 参数），用作输入子目录名与血缘文件名 | String | 是 |
| file | 输入 zip 二进制流（流式落盘 ≤2GB；解压抹平层级；同一 uniqueId 重传先清空旧素材） | File | 是 |

`/predict` 参数（请求体 JSON）：

| 参数名称 | 描述 | 类型 | 是否必传 |
| --- | --- | --- | --- |
| uniqueId | 任务唯一标识（阶段首算子凭它取素材） | String | 是 |
| inputFile | 上游算子响应的 data.outputFile（链路中段必传；路径闸门校验） | String | 否 |
| isLastOperator | 是否阶段末算子（true 时输出收口 <run_id>_stage_output.zip） | Boolean | 否 |
| dpi | 页图渲染 DPI，默认 150；须在 72–300 | Number | 否 |
| max_context_chars | 上下文文本上限，默认 2000（交付说明固定 2000，此处仅预留）；须 ≥200 | Number | 否 |
| concurrency | 逐页定位并发，默认 4，上限 8 | Number | 否 |

阶段首算子：不带 inputFile；环节② fml_formula_recognize 接续。请求示例：

```bash
curl -X POST http://127.0.0.1:6288/predict \
  -H "Content-Type: application/json" \
  -d '{"uniqueId":"fml001","isLastOperator":false}'
```

输入内容版式：`.pdf` / `.zip`。

---

##### 公式区域定位与裁切-输出示例

结果写入输出目录 `<OUTPUT_DIR>/fml_formula_locate_<run_id>/`，`isLastOperator=true` 时整目录收口为 `<run_id>_stage_output.zip`：

| 文件 | 编码 | 说明 |
| --- | --- | --- |
| `pages/<docId>/*.png` | PNG | 逐页渲染图（定位与裁切的底图） |
| `crops/<docId>/<instanceId>.png` | PNG | 公式裁切图（环节②识别输入） |
| `records.jsonl` | UTF-8 | 一 PDF 一行：instances[{instanceId,pageNo,bbox,bboxPixel,hasNumber,locateConfidence,crop,chapterTitle,contextText}] + instanceCount |
| `lineage_<uniqueId>.jsonl` | UTF-8 | 逐 PDF keep（带 instances 计数）/ fail；跳过明细（页定位失败/坐标校验失败/裁切过小） |

> 复核对接口径：`/predict` 响应 `data.skipped[]` / `data.failed[]` 条目同样带 `code`（如 `unsupported_suffix`、`pdf_encrypted`、`model_call_failed`）。同一行命中多个条件时只取优先级最高的一个码，无预设条件命中时为 `unclassified`。

`/predict` 成功响应（统一信封）：

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "outputFile": "<OUTPUT_DIR>/fml_formula_locate_<run_id>/",
    "lineageFile": "<OUTPUT_DIR>/fml_formula_locate_<run_id>/lineage_<run_id>.jsonl",
    "summary": {...},
    "skipped": [{"name": "...", "reason": "...", "code": "unsupported_suffix"}],
    "failed": [{"name": "...", "reason": "...", "code": "model_call_failed"}]
  }
}
```

主成果行示例（一行）：

```jsonl
{"docId":"formula_sample","fileName":"formula_sample.pdf","pageCount":2,"checksum":"<sha256>","instanceCount":3,"instances":[{"instanceId":"formula_sample-p1-f02","pageNo":1,"bbox":[288,305,890,365],"bboxPixel":[214,227,662,271],"hasNumber":true,"locateConfidence":0.95,"crop":"crops/formula_sample/formula_sample-p1-f02.png","chapterTitle":"第二章 公式","contextText":"其中 a、b 为已知常量，x 为自变量，c_i 为第 i 项系数……"}]}
```
