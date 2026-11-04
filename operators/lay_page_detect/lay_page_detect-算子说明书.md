# 算子模型设计

## 逐页版面检测

### 逐页版面检测

#### 逐页版面检测

##### 基础信息

| 分类 | 字段 | 值 |
| --- | --- | --- |
| 基础信息 | 模型编号 | `lay_page_detect`（编号起区分作用，平台正式编号于交付前统一分配替换） |
| 基础信息 | 模型名称 | 逐页版面检测 |
| 基础信息 | 模型版本号 | v1.0.0 |
| 基础信息 | 所属产线 | 复杂版面 · 环节② 逐页检测 + 环节③ 质量校验汇总（产线末位） |
| 基础信息 | 技术形态 | 视觉大模型（逐页检测）+ 规则分流 |
| 基础信息 | 链路位置 | 链路第 2 环（末位）：接 lay_page_render 产物；isLastOperator=true 收口 |
| 基础信息 | 输入类型 | 上游 records.jsonl + pages/ 页图（inputFile 指向上游输出目录） |
| 基础信息 | 输出类型 | records.jsonl（一页一行数据集）+ review.jsonl（问题页）+ visual/ 框选图层 + 血缘 JSONL + 阶段 zip |
| 基础信息 | 技术栈 | Python 3.12、requests（VL 模型多模态调用）+ Pillow（框选图层）+ ThreadPoolExecutor；HTTP 层 FastAPI + uvicorn。模型 Qwen/Qwen3-VL-32B-Instruct（硅基流动） |
| 功能定义 | 模型定义 | 交付说明环节②③ + §4.1/§4.2 Prompt 原文：逐页输出元素（type/bbox/readingOrder/structureTree/双置信度）→ §4.6 后处理校验 → 规则分流（六类）→ 汇总（环节③只汇总不自检） |
| 功能定义 | 能力边界 | 不做 OCR 不提取文字（§4.1 硬性约束 2）；只排本页阅读顺序；规则分流只标记不裁决（复核人工裁定）；系统性错误重跑②时旧复核单作废是平台侧职责 |
| 功能定义 | 适用场景 | 复杂版面产线核心环：页图 → 结构化版面元素 + 问题页分流，一页一行进数据集 |
| 输出内容描述 | 内容来源 | 元素框与类型由模型基于页图判定；页图原样透传，另生成框选图层（原图 + 框线，复核可视化用） |
| 输出内容描述 | 编码格式 | 全部 JSONL/TXT 产物 UTF-8；图片 PNG；阶段收口 zip |
| 输出内容描述 | 输出内容类型 | records.jsonl（一页一行：pageId=docId-#页号 / elementCount / elements[{elementId,type,bbox,readingOrder,bboxConf,typeConf}] / structureTree / readingOrder / confidence / lowConfidenceCount / lowConfidenceReasons / reviewStatus）；visual/*.png（页图 + 红框 + elementId:type 标注（复核可视化））；review.jsonl（问题页整行 + reviewReason（六类规则命中项）；<run_id>_stage_output.zip（isLastOperator=true 时整目录收口） |

---

##### 技术方案

```text
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
```

**六类分流全部落地**：交付说明环节②规则：框选 <0.8 或判定 <0.8、重叠 IoU>0.3、越界、顺序重号/缺号、空页 → 进复核。越界在规范化层截断修正并标记（框可用但需人看）；顺序冲突不阻断（§4.6：交给规则分流）

**bbox 0–1000 归一化**：交付说明 §4.1 坐标口径；Qwen3-VL grounding 冒烟已验证该坐标系稳定（6 元素类型/bbox/顺序全对）。框选图层按页图实际尺寸换算回像素绘制

**环节③只汇总**：交付说明环节③：汇总元素结果、失败页清单、复核结论，不做自检——本算子输出即汇总形态（一页一行 + 失败页清单 + 复核清单），问题页只追加平台复核单

**长边 1600px**：交付说明 §4.5 建议 1600–2000px；实测 2000px 单页 60s 超时、1600px 约 17s，取下限保证 60s 超时预算内稳定

---

##### 技术实现

| 分类 | 字段 | 值 |
| --- | --- | --- |
| 训练方式 | 不涉及。本算子无训练过程；阈值、枚举、Prompt 全文以集中显式常量实现（configs/config.py、configs/prompts.py），逐项可查、可审计 |
| 基础模型 | 外部大模型 API：Qwen/Qwen3-VL-32B-Instruct（硅基流动） |
| 训练数据集 | 不涉及。不使用任何训练语料 |
| 测试数据集 | 包内自带（dataset/sample/）：dataset/sample/ = 上游真实产物（records.jsonl + pages/ 页图 3 张）；上游算子真实产物副本（链路冒烟实跑输出）。离线用例 mock 模型调用，联网冒烟用例直连真实 API |

**部署与运行**（完整验收步骤见 `lay_page_detect-测试指令.md`）：

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
python -m pytest lay_page_detect/tests -q
```

---

##### 资源要求

| 项目 | 实测 / 说明 |
| --- | --- |
| 实测最小配置 · CPU | 单核可运行（受限并发为线程池，无进程并行） |
| 实测最小配置 · 内存 | 服务本体 + FastAPI 栈 < 200 MB；图片解码峰值按单图长边 1600 px 约 8 MB 位图估 |
| 实测最小配置 · 磁盘 | 镜像装载内容约 1 MB 级（inference.py + 内层包 + 样本）；单次运行产出见输出说明，成果只增不减由平台按 outputFile 管理 |
| 是否需要 GPU | 不需要。无本地权重；模型调用在远端 API |
| 实测数据规模 | 包内样本全量（dataset/sample/ = 上游真实产物（records.jsonl + pages/ 页图 3 张）），单请求完整跑通全部分支 |
| 是否依赖外部 API | 是：硅基流动（SILICONFLOW_BASE_URL/SILICONFLOW_API_KEY 可覆盖）；调用约定见技术实现 |
| 单次运行耗时 | 单页约 17 s（Qwen3-VL-32B，1600px）；3 页并发 4 约 40 s |
| 辅助模块依赖 | 运行必需：fastapi==0.116.1, uvicorn==0.51.0, python-multipart==0.0.32, starlette==0.47.3, pydantic==2.13.4, requests==2.34.2, pillow==12.0.0（与 requirements.txt 一致，版本锁定）；测试依赖：pytest==8.3.4 |

---

##### 训练后的模型性能指标

> 本算子无训练过程，不存在模型性能指标；下表为可复现的验证指标——全部由包内单元测试实际断言或真实 API 冒烟实跑得出，可用测试指令复现。

| 指标 | 数值 | 说明 |
| --- | --- | --- |
| 离线单元测试 | 4 / 4 通过 | 六类分流规则各命中一次（干净/框选低/判定低/重叠/越界截断/顺序重号/空页）+ 模型失败页 + 渲染失败页汇入；pageNo 不符重试 1 次后进失败页；IoU 直测 |
| 真实 API 冒烟 | 3 页全对 | p1 双栏 6 元素（header/heading/body/figure/body/footer）类型与顺序全对；p2 表+公式识别；p3 空页正确进复核 |
| 端到端链路 | .scratch/chain_lay.py 全通 | uploadFile → render → detect → stage zip；一页一行 3 行 + 框选图层 2 张（空页无图层） |

##### 执行结果截图

| 项目 | 内容 |
| --- | --- |
| 执行结果截图 | [[执行结果截图:逐页版面检测（复杂版面）运行实录]] |

图 1　逐页版面检测（复杂版面）执行结果截图。

---

##### 逐页版面检测-输入示例

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
| confidence_threshold | 低置信阈值（框选/判定共用），默认 0.8（交付说明 §八：任务级可调） | Number | 否 |
| iou_threshold | 重叠判定 IoU 阈值，默认 0.3（交付说明 §八：固定 0.3，此处仅预留） | Number | 否 |
| concurrency | 逐页调用并发，默认 4，上限 8 | Number | 否 |
| draw_overlay | 是否生成框选图层，默认 true | Boolean | 否 |

产线末位：isLastOperator=true 收口阶段 zip。请求示例：

```bash
curl -X POST http://127.0.0.1:6288/predict \
  -H "Content-Type: application/json" \
  -d '{"inputFile":"<上游 outputFile>","isLastOperator":true}'
```

输入内容版式：`.jsonl` / `.zip`（链路中段，经 inputFile 接续）。

---

##### 逐页版面检测-输出示例

结果写入输出目录 `<OUTPUT_DIR>/lay_page_detect_<run_id>/`，`isLastOperator=true` 时整目录收口为 `<run_id>_stage_output.zip`：

| 文件 | 编码 | 说明 |
| --- | --- | --- |
| `records.jsonl` | UTF-8 | 一页一行：pageId=docId-#页号 / elementCount / elements[{elementId,type,bbox,readingOrder,bboxConf,typeConf}] / structureTree / readingOrder / confidence / lowConfidenceCount / lowConfidenceReasons / reviewStatus |
| `visual/*.png` | PNG | 页图 + 红框 + elementId:type 标注（复核可视化） |
| `review.jsonl` | UTF-8 | 问题页整行 + reviewReason（六类规则命中项，分号连接） |
| `<run_id>_stage_output.zip` | zip | isLastOperator=true 时整目录收口 |

> 复核对接口径：`review.jsonl` 每行在完整记录之外带 `reviewReason`（中文，供复核员阅读）与 `code`（小写下划线机器码，如 `low_confidence`、`model_call_failed`，供平台按类型生成复核单）；`/predict` 响应 `data.skipped[]` / `data.failed[]` 条目同样带 `code`（如 `unsupported_suffix`、`pdf_encrypted`、`model_call_failed`）。同一行命中多个条件时只取优先级最高的一个码，无预设条件命中时为 `unclassified`。

`/predict` 成功响应（统一信封）：

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "outputFile": "<OUTPUT_DIR>/<run_id>_stage_output.zip",
    "lineageFile": "<OUTPUT_DIR>/lay_page_detect_<run_id>/lineage_<run_id>.jsonl",
    "summary": {...},
    "skipped": [{"name": "...", "reason": "...", "code": "unsupported_suffix"}],
    "failed": [{"name": "...", "reason": "...", "code": "model_call_failed"}]
  }
}
```

主成果行示例（一行）：

```jsonl
{"pageId":"layout_sample-#1","docId":"layout_sample","pageNo":1,"elementCount":6,"elements":[{"elementId":"p1-e1","type":"header","bbox":[66,25,231,38],"readingOrder":1,"bboxConf":0.95,"typeConf":0.95}],"structureTree":[],"readingOrder":[1,2,3,4,5,6],"confidence":{"bbox":0.9,"type":0.9},"lowConfidenceCount":0,"lowConfidenceReasons":"","reviewStatus":"未进入复核","revisionStatus":"—"}
```
