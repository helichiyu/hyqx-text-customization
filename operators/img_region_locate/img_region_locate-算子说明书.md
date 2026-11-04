# 算子模型设计

## 图片区域定位与裁切

### 图片区域定位与裁切

#### 图片区域定位与裁切

##### 基础信息

| 分类 | 字段 | 值 |
| --- | --- | --- |
| 基础信息 | 模型编号 | `img_region_locate`（编号起区分作用，平台正式编号于交付前统一分配替换） |
| 基础信息 | 模型名称 | 图片区域定位与裁切 |
| 基础信息 | 模型版本号 | v1.0.0 |
| 基础信息 | 所属产线 | 图文融合 · 环节① 图片接入与判型 |
| 基础信息 | 技术形态 | CV/规则（不调模型） |
| 基础信息 | 链路位置 | 阶段首算子：凭 uniqueId 取上传素材；输出供 img_type_classify 接续 |
| 基础信息 | 输入类型 | 一个 zip 或散文件（JPG/PNG/BMP/WebP/TIFF，按文件名升序处理） |
| 基础信息 | 输出类型 | regions/ 处理后图片 + records.jsonl（ImageRegion 登记）+ 血缘 JSONL |
| 基础信息 | 技术栈 | Python 3.12、Pillow（四角背景色基准 + 差分掩码 + 裁切）；HTTP 层 FastAPI + uvicorn。不调模型、不引入 OpenCV |
| 功能定义 | 模型定义 | 交付说明环节① #2：区域定位与裁切（CV/规则，不调模型）——实现口径：整图直通 + 拍照件黑边/白边自动裁剪 |
| 功能定义 | 能力边界 | 口径说明：交付说明未给出「区域」语义与原型（待确认 Q1），按整图直通 + 均色边框裁剪实现；重试 2 次仍失败跳过并记录（交付说明固定口径）。不做目标检测、不做主体分割 |
| 功能定义 | 适用场景 | 图文融合产线第一环：图片可用性校验与内容区裁剪，登记 ImageRegion 供判型与描述消费 |
| 输出内容描述 | 内容来源 | 处理后图片来自上传图片的裁剪（无边框时原样直通）；不构造、不增强任何像素内容 |
| 输出内容描述 | 编码格式 | 全部 JSONL/TXT 产物 UTF-8；图片 PNG；阶段收口 zip |
| 输出内容描述 | 输出内容类型 | regions/<imageId>.png（处理后图片（直通或裁边后）；records.jsonl（一图一行：imageId / fileName / image / region{bbox,cropped,width,height,sourceWidth,sourceHeight}）；lineage_<uniqueId>.jsonl（逐图 keep（带 cropped 与尺寸）/ skip（区域定位失败） |

---

##### 技术方案

```text
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
```

**「区域定位」的实现口径（待确认 Q1）**：交付说明环节① #2 只写「CV/规则，不调模型」，未定义定位对象。默认按整图直通 + 均色边框（拍照黑边/扫描白边）裁剪实现；若甲方指其它语义（如主体检测），需原型或举例后替换本算子

**四角基准而非固定颜色**：拍照黑边、扫描白边、网页截图灰边颜色各异；取四角均值自适应判定背景，容差 18（0–255）排除 JPEG 噪声

**重试语义**：交付说明固定口径：区域定位重试 2 次（共 3 次机会）仍失败 → 跳过并记录「区域定位失败」；本实现纯确定性 CV，重试主要兜瞬时文件句柄/解码异常

---

##### 技术实现

| 分类 | 字段 | 值 |
| --- | --- | --- |
| 训练方式 | 不涉及。本算子无训练过程；阈值、枚举、Prompt 全文以集中显式常量实现（configs/config.py、configs/prompts.py），逐项可查、可审计 |
| 基础模型 | 不涉及。无预训练权重、无本地推理；规则与确定性计算实现（纯标准库/PyMuPDF/Pillow）。 |
| 训练数据集 | 不涉及。不使用任何训练语料 |
| 测试数据集 | 包内自带（dataset/sample/）：dataset/sample/ = 5 张图（几何半圆、折线图、表格、流程示意、低分辨率三角形）；由样本生成脚本确定性生成（_shared_tools/make_samples/）。离线用例 mock 模型调用，联网冒烟用例直连真实 API |

**部署与运行**（完整验收步骤见 `img_region_locate-测试指令.md`）：

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
python -m pytest img_region_locate/tests -q
```

---

##### 资源要求

| 项目 | 实测 / 说明 |
| --- | --- |
| 实测最小配置 · CPU | 单核可运行（受限并发为线程池，无进程并行） |
| 实测最小配置 · 内存 | 服务本体 + FastAPI 栈 < 200 MB；图片解码峰值按单图长边 1600 px 约 8 MB 位图估 |
| 实测最小配置 · 磁盘 | 镜像装载内容约 1 MB 级（inference.py + 内层包 + 样本）；单次运行产出见输出说明，成果只增不减由平台按 outputFile 管理 |
| 是否需要 GPU | 不需要。无本地权重；模型调用在远端 API |
| 实测数据规模 | 包内样本全量（dataset/sample/ = 5 张图（几何半圆、折线图、表格、流程示意、低分辨率三角形）），单请求完整跑通全部分支 |
| 是否依赖外部 API | 否：运行期无网络请求 |
| 单次运行耗时 | 5 张图全量 < 1 s（纯 CPU）；不依赖网络 |
| 辅助模块依赖 | 运行必需：fastapi==0.116.1, uvicorn==0.51.0, python-multipart==0.0.32, starlette==0.47.3, pydantic==2.13.4, pillow==12.0.0（与 requirements.txt 一致，版本锁定）；测试依赖：pytest==8.3.4 |

---

##### 训练后的模型性能指标

> 本算子无训练过程，不存在模型性能指标；下表为可复现的验证指标——全部由包内单元测试实际断言或真实 API 冒烟实跑得出，可用测试指令复现。

| 指标 | 数值 | 说明 |
| --- | --- | --- |
| 离线单元测试 | 5 / 5 通过 | 白底内容图直通不裁、黑边图精确裁出内容 bbox [60,50,340,250]、样本池 5 张全过、损坏图重试 3 次（计数断言）后跳过、参数校验 |
| 真实样本 | 5/5 通过 | matplotlib/PIL 生成的样本含均匀边缘被正确裁剪；裁剪输出图完整可开 |
| 确定性 | 同图两次处理字节一致 | 纯 Pillow 确定性操作，不联网 |

##### 执行结果截图

| 项目 | 内容 |
| --- | --- |
| 执行结果截图 | [[执行结果截图:图片区域定位与裁切（图文融合）运行实录]] |

图 1　图片区域定位与裁切（图文融合）执行结果截图。

---

##### 图片区域定位与裁切-输入示例

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
| border_tolerance | 边框判定容差（0–255），默认 18；差异低于容差视为背景 | Number | 否 |
| min_crop_size | 裁剪后最小保留边长（px），默认 32；过小判异常 | Number | 否 |

阶段首算子：不带 inputFile；判型 img_type_classify 接续。请求示例：

```bash
curl -X POST http://127.0.0.1:6288/predict \
  -H "Content-Type: application/json" \
  -d '{"uniqueId":"img001","isLastOperator":false}'
```

输入内容版式：`.jpg` / `.jpeg` / `.png` / `.bmp` / `.webp` / `.tif` / `.tiff` / `.zip`。

---

##### 图片区域定位与裁切-输出示例

结果写入输出目录 `<OUTPUT_DIR>/img_region_locate_<run_id>/`，`isLastOperator=true` 时整目录收口为 `<run_id>_stage_output.zip`：

| 文件 | 编码 | 说明 |
| --- | --- | --- |
| `regions/<imageId>.png` | PNG | 处理后图片（直通或裁边后，统一转 RGB PNG） |
| `records.jsonl` | UTF-8 | 一图一行：imageId / fileName / image / region{bbox,cropped,width,height,sourceWidth,sourceHeight} |
| `lineage_<uniqueId>.jsonl` | UTF-8 | 逐图 keep（带 cropped 与尺寸）/ skip（区域定位失败，含重试次数） |

> 复核对接口径：`/predict` 响应 `data.skipped[]` / `data.failed[]` 条目同样带 `code`（如 `unsupported_suffix`、`pdf_encrypted`、`model_call_failed`）。同一行命中多个条件时只取优先级最高的一个码，无预设条件命中时为 `unclassified`。

`/predict` 成功响应（统一信封）：

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "outputFile": "<OUTPUT_DIR>/img_region_locate_<run_id>/",
    "lineageFile": "<OUTPUT_DIR>/img_region_locate_<run_id>/lineage_<run_id>.jsonl",
    "summary": {...},
    "skipped": [{"name": "...", "reason": "...", "code": "unsupported_suffix"}],
    "failed": [{"name": "...", "reason": "...", "code": "model_call_failed"}]
  }
}
```

主成果行示例（一行）：

```jsonl
{"imageId":"geometry_001","fileName":"geometry_001.png","image":"regions/geometry_001.png","region":{"bbox":[38,25,962,878],"cropped":true,"width":924,"height":853,"sourceWidth":1000,"sourceHeight":900}}
```
