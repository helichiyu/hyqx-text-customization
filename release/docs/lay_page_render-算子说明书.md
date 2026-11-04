# 算子模型设计

## 版面分页渲染

### 版面分页渲染

#### 版面分页渲染

##### 基础信息

| 分类 | 字段 | 值 |
| --- | --- | --- |
| 基础信息 | 模型编号 | `lay_page_render`（编号起区分作用，平台正式编号于交付前统一分配替换） |
| 基础信息 | 模型名称 | 版面分页渲染 |
| 基础信息 | 模型版本号 | v1.0.0 |
| 基础信息 | 所属产线 | 复杂版面 · 环节① 文档接入与分页 |
| 基础信息 | 技术形态 | 规则（PDF 渲染，不调模型） |
| 基础信息 | 链路位置 | 阶段首算子：凭 uniqueId 取上传素材；输出供 lay_page_detect 接续 |
| 基础信息 | 输入类型 | 一个 zip 或散文件（PDF，按文件名升序处理） |
| 基础信息 | 输出类型 | pages/<docId>/ 页图 PNG + records.jsonl（含 PageManifest 与页清单）+ 血缘 JSONL |
| 基础信息 | 技术栈 | Python 3.12、PyMuPDF（打开校验 + 逐页 pixmap 渲染）+ hashlib（SHA-256）；HTTP 层 FastAPI + uvicorn。不引入 OCR/深度学习框架 |
| 功能定义 | 模型定义 | 交付说明环节① #2–#6：打开 PDF 校验加密/损坏 → 逐页渲染（默认 150 DPI）→ 生成 PageManifest（docId、pageCount、format、pageRange、checksum）→ 校验页数 >0 → 页图 + 页号交环节② |
| 功能定义 | 能力边界 | 只做渲染与清单，不做版面检测（环节②职责）；单页渲染失败只跳过该页进失败页清单，不牵连整份；整份加密/损坏/0 页进失败清单（任务待处理口径） |
| 功能定义 | 适用场景 | 复杂版面产线第一环：把 PDF 变成逐页图片与可校验的页清单 |
| 输出内容描述 | 内容来源 | 页图由上传 PDF 渲染生成（MuPDF pixmap）；checksum 为 PDF 原文件 SHA-256，不改动上传原件 |
| 输出内容描述 | 编码格式 | 全部 JSONL/TXT 产物 UTF-8；图片 PNG；阶段收口 zip |
| 输出内容描述 | 输出内容类型 | pages/<docId>/*.png（逐页渲染图）；records.jsonl（一 PDF 一行：manifest{docId,pageCount,format,pageRange,checksum} + pages[] + failedPages[{pageNo,reason}]）；lineage_<uniqueId>.jsonl（逐 PDF keep（带 pages 计数）/ fail（加密/损坏/0 页/全部页失败）） |

---

##### 技术方案

```text
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
```

**DPI 默认 150**：交付说明 §八：渲染 DPI 默认 150、可配 150–200（任务快照）；本算子放开 72–300 校验区间，默认与交付口径一致

**单页失败隔离**：交付说明环节①：单页渲染失败 → 失败页清单，不送环节②。渲染循环逐页 try/except，一页失败不影响其余页；环节② 会把 failedPages 汇总进自己的失败页清单

**checksum 用途**：页清单的 SHA-256 供平台核对素材唯一性与重跑一致性（同一 PDF 重跑 checksum 不变）

---

##### 技术实现

| 分类 | 字段 | 值 |
| --- | --- | --- |
| 训练方式 | 不涉及。本算子无训练过程；阈值、枚举、Prompt 全文以集中显式常量实现（configs/config.py、configs/prompts.py），逐项可查、可审计 |
| 基础模型 | 不涉及。无预训练权重、无本地推理；规则与确定性计算实现（纯标准库/PyMuPDF/Pillow）。 |
| 训练数据集 | 不涉及。不使用任何训练语料 |
| 测试数据集 | 包内自带（dataset/sample/）：dataset/sample/ = layout_sample.pdf（3 页：双栏+图+表+公式+空白页）+ encrypted.pdf（加密负例）；由样本生成脚本确定性生成（_shared_tools/make_samples/）。离线用例 mock 模型调用，联网冒烟用例直连真实 API |

**部署与运行**（完整验收步骤见 `lay_page_render-测试指令.md`）：

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

**不依赖外部 API**：纯规则实现，运行期无网络请求（测试依赖除外）。

**复跑包内冒烟用例**（从交付包根运行）：

```bash
cd <交付包根>
python -m pytest lay_page_render/tests -q
```

---

##### 资源要求

| 项目 | 实测 / 说明 |
| --- | --- |
| 实测最小配置 · CPU | 单核可运行（受限并发为线程池，无进程并行） |
| 实测最小配置 · 内存 | 服务本体 + FastAPI 栈 < 200 MB；PDF 渲染峰值随页数与 DPI 线性（150 DPI A4 单页约 6 MB 位图） |
| 实测最小配置 · 磁盘 | 镜像装载内容约 1 MB 级（inference.py + 内层包 + 样本）；单次运行产出见输出说明，成果只增不减由平台按 outputFile 管理 |
| 是否需要 GPU | 不需要。无本地权重；模型调用在远端 API |
| 实测数据规模 | 包内样本全量（dataset/sample/ = layout_sample.pdf（3 页），单请求完整跑通全部分支 |
| 是否依赖外部 API | 否：运行期无网络请求 |
| 单次运行耗时 | 3 页 PDF 渲染约 1 s（150 DPI，纯 CPU）；不依赖网络 |
| 辅助模块依赖 | 运行必需：fastapi==0.116.1, uvicorn==0.51.0, python-multipart==0.0.32, starlette==0.47.3, pydantic==2.13.4, pymupdf==1.28.2（与 requirements.txt 一致，版本锁定）；测试依赖：pytest==8.3.4 |

---

##### 训练后的模型性能指标

> 本算子无训练过程，不存在模型性能指标；下表为可复现的验证指标——全部由包内单元测试实际断言或真实 API 冒烟实跑得出，可用测试指令复现。

| 指标 | 数值 | 说明 |
| --- | --- | --- |
| 离线单元测试 | 6 / 6 通过 | 渲染 + PageManifest 字段、加密失败、损坏与 0 页失败、单页失败隔离（第 2 页炸仍出 1/3 页）、全部页失败整份出局、参数校验 |
| 真实链路 | 2 PDF → 1 成功（3 页）+ 1 加密失败 | 加密 PDF 正确进失败清单；页图尺寸 1240x1754（150DPI A4） |
| 幂等 | 同一 PDF 两次渲染页图字节一致 | MuPDF 确定性渲染，无随机成分 |

##### 执行结果截图

| 项目 | 内容 |
| --- | --- |
| 执行结果截图 | [[执行结果截图:版面分页渲染（复杂版面）运行实录]] |

图 1　版面分页渲染（复杂版面）执行结果截图。

---

##### 版面分页渲染-输入示例

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
| dpi | 渲染 DPI，默认 150（交付说明建议 150–200）；须在 72–300 | Number | 否 |
| image_format | 页图格式，默认 png；可选 jpg | String | 否 |

阶段首算子：不带 inputFile；环节② lay_page_detect 接续。请求示例：

```bash
curl -X POST http://127.0.0.1:6288/predict \
  -H "Content-Type: application/json" \
  -d '{"uniqueId":"lay001","isLastOperator":false}'
```

输入内容版式：`.pdf` / `.zip`。

---

##### 版面分页渲染-输出示例

结果写入输出目录 `<OUTPUT_DIR>/lay_page_render_<run_id>/`，`isLastOperator=true` 时整目录收口为 `<run_id>_stage_output.zip`：

| 文件 | 编码 | 说明 |
| --- | --- | --- |
| `pages/<docId>/*.png` | PNG | 逐页渲染图，文件名 <docId>_p<页号4位>.png，尺寸随 DPI |
| `records.jsonl` | UTF-8 | 一 PDF 一行：manifest{docId,pageCount,format,pageRange,checksum} + pages[] + failedPages[{pageNo,reason}] |
| `lineage_<uniqueId>.jsonl` | UTF-8 | 逐 PDF keep（带 pages 计数）/ fail（加密/损坏/0 页/全部页失败） |

> 复核对接口径：`/predict` 响应 `data.skipped[]` / `data.failed[]` 条目同样带 `code`（如 `unsupported_suffix`、`pdf_encrypted`、`model_call_failed`）。同一行命中多个条件时只取优先级最高的一个码，无预设条件命中时为 `unclassified`。

`/predict` 成功响应（统一信封）：

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "outputFile": "<OUTPUT_DIR>/lay_page_render_<run_id>/",
    "lineageFile": "<OUTPUT_DIR>/lay_page_render_<run_id>/lineage_<run_id>.jsonl",
    "summary": {...},
    "skipped": [{"name": "...", "reason": "...", "code": "unsupported_suffix"}],
    "failed": [{"name": "...", "reason": "...", "code": "model_call_failed"}]
  }
}
```

主成果行示例（一行）：

```jsonl
{"docId":"layout_sample","fileName":"layout_sample.pdf","manifest":{"docId":"layout_sample","pageCount":3,"format":"pdf","pageRange":[1,3],"checksum":"<sha256-64位>"},"pages":[{"pageNo":1,"image":"pages/layout_sample/layout_sample_p0001.png","width":1240,"height":1754}],"failedPages":[]}
```
