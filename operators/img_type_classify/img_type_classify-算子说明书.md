# 算子模型设计

## 图片判型

### 图片判型

#### 图片判型

##### 基础信息

| 分类 | 字段 | 值 |
| --- | --- | --- |
| 基础信息 | 模型编号 | `img_type_classify`（编号起区分作用，平台正式编号于交付前统一分配替换） |
| 基础信息 | 模型名称 | 图片判型 |
| 基础信息 | 模型版本号 | v1.0.0 |
| 基础信息 | 所属产线 | 图文融合 · 环节① 图片接入与判型 |
| 基础信息 | 技术形态 | 视觉大模型（判型） |
| 基础信息 | 链路位置 | 链路第 2 环：接 img_region_locate 产物；输出供 img_struct_describe 接续 |
| 基础信息 | 输入类型 | 上游 records.jsonl + regions/ 图片；predict 必带参数 category（任务大类） |
| 基础信息 | 输出类型 | records.jsonl（匹配图片，imageType 并入，图片随记录复制保持输出自包含）+ review.jsonl（低置信）+ 血缘 JSONL |
| 基础信息 | 技术栈 | Python 3.12、requests（VL 调用）+ ThreadPoolExecutor；HTTP 层 FastAPI + uvicorn。模型 Qwen/Qwen3-VL-32B-Instruct |
| 功能定义 | 模型定义 | 交付说明环节① #3#4 + §4.3.1 Prompt 原文：大类一致性校验（与任务所选比对，不一致跳过）+ 子类判定（match/子类/置信度/依据） |
| 功能定义 | 能力边界 | 大类不一致 match=false → 跳过该图记录「大类不一致」；判型置信度 <0.8 → 进复核（继续下游）；子类只能从给定列表选。不做要素提取与描述（环节②③职责） |
| 功能定义 | 适用场景 | 图文融合产线的分类闸：任务选了大类，只有匹配的图进要素提取与描述 |
| 输出内容描述 | 内容来源 | 判定结论由模型基于处理后图片生成；图片与上游记录原样透传（匹配图片复制进本算子输出，链路自包含） |
| 输出内容描述 | 编码格式 | 全部 JSONL/TXT 产物 UTF-8；图片 PNG；阶段收口 zip |
| 输出内容描述 | 输出内容类型 | records.jsonl（匹配图片一图一行：上游字段 + imageType{match,category,subtype,confidence,reason,taskCategory}）；regions/（匹配图片副本（输出自包含）；review.jsonl（判型低置信/输出非法待复核 + reviewReason）；lineage_<run_id>.jsonl（逐图 keep（带 type_confidence）/ skip（大类不一致）/ fail） |

---

##### 技术方案

```text
/predict（inputFile = 上游 img_region_locate 输出目录；category 必填）
   ↓  读 records.jsonl；逐图并发（4–8）
每图（§4.3.1 System 原文 + User「任务大类：{category}；这是第 N 张图片…」）：
   ↓  §4.3.0 公共约定并入 System（只述可见事实/uncertain/禁 1.0）
   ↓  输出校验：category 越枚举 / subtype 越枚举 / match 非布尔 → 重试 1 次
   ↓  置信度截断 [0,0.98]
路由：
   ↓  输出持续非法          → failed + review（不进下游）
   ↓  match=false           → 跳过清单（大类不一致（任务=X，实判=Y））
   ↓  match=true            → records.jsonl（imageType 并入），图片复制进输出
   ↓  置信度 <0.8           → 追加 review（判型置信度低于阈值），仍进下游
```

**category 是任务参数**：交付说明环节① #3：大类一致性校验与任务所选比对——category（几何/统计/表格/示意）由平台按任务传入 predict，算子不猜

**跳过原因带双方大类**：跳过记录写明任务大类与实判大类（如「任务=几何，实判=统计」），复核/平台可直接消费

**输出自包含**：匹配图片复制进本算子输出目录（regions/ 同结构）——链路传输时下游 img_struct_describe 拿到的 inputFile 是本算子输出，取图不依赖上游目录

---

##### 技术实现

| 分类 | 字段 | 值 |
| --- | --- | --- |
| 训练方式 | 不涉及。本算子无训练过程；阈值、枚举、Prompt 全文以集中显式常量实现（configs/config.py、configs/prompts.py），逐项可查、可审计 |
| 基础模型 | 外部大模型 API：Qwen/Qwen3-VL-32B-Instruct |
| 训练数据集 | 不涉及。不使用任何训练语料 |
| 测试数据集 | 包内自带（dataset/sample/）：dataset/sample/ = 上游真实产物（records.jsonl + regions/ 5 张图）；上游算子真实产物副本（链路冒烟实跑输出）。离线用例 mock 模型调用，联网冒烟用例直连真实 API |

**部署与运行**（完整验收步骤见 `img_type_classify-测试指令.md`）：

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
python -m pytest img_type_classify/tests -q
```

---

##### 资源要求

| 项目 | 实测 / 说明 |
| --- | --- |
| 实测最小配置 · CPU | 单核可运行（受限并发为线程池，无进程并行） |
| 实测最小配置 · 内存 | 服务本体 + FastAPI 栈 < 200 MB；纯文本处理，无媒体位图峰值 |
| 实测最小配置 · 磁盘 | 镜像装载内容约 1 MB 级（inference.py + 内层包 + 样本）；单次运行产出见输出说明，成果只增不减由平台按 outputFile 管理 |
| 是否需要 GPU | 不需要。无本地权重；模型调用在远端 API |
| 实测数据规模 | 包内样本全量（dataset/sample/ = 上游真实产物（records.jsonl + regions/ 5 张图）），单请求完整跑通全部分支 |
| 是否依赖外部 API | 是：硅基流动（SILICONFLOW_BASE_URL/SILICONFLOW_API_KEY 可覆盖）；调用约定见技术实现 |
| 单次运行耗时 | 单张判型约 8–15 s；5 张并发 4 约 20 s |
| 辅助模块依赖 | 运行必需：fastapi==0.116.1, uvicorn==0.51.0, python-multipart==0.0.32, starlette==0.47.3, pydantic==2.13.4, requests==2.34.2（与 requirements.txt 一致，版本锁定）；测试依赖：pytest==8.3.4 |

---

##### 训练后的模型性能指标

> 本算子无训练过程，不存在模型性能指标；下表为可复现的验证指标——全部由包内单元测试实际断言或真实 API 冒烟实跑得出，可用测试指令复现。

| 指标 | 数值 | 说明 |
| --- | --- | --- |
| 离线单元测试 | 4 / 4 通过 | 匹配保留/不一致跳过/低置信复核三分支、子类越枚举重试 1 次后失败、模型失败分流、category 必填校验 |
| 真实 API 冒烟 | 四类各一遍全对 | 5 张图对 4 个任务大类分别判定：每类恰好匹配 1–2 张、其余 3–4 张大类不一致跳过且实判大类正确；子类全部在枚举内 |
| 枚举兜底 | 越枚举重试后失败不静默 | subtype 只从给定列表选（§4.3.1 规则），越枚举视为输出非法 |

##### 执行结果截图

| 项目 | 内容 |
| --- | --- |
| 执行结果截图 | [[执行结果截图:图片判型（图文融合）运行实录]] |

图 1　图片判型（图文融合）执行结果截图。

---

##### 图片判型-输入示例

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
| category | 任务大类：几何 / 统计 / 表格 / 示意；缺失或非法 predict 整体报错（code=1） | String | 是 |
| confidence_threshold | 判型置信度阈值，默认 0.8；低于进复核不阻断 | Number | 否 |
| concurrency | 逐图调用并发，默认 4，上限 8 | Number | 否 |

必带 category；链路中段经 inputFile 接续。请求示例：

```bash
curl -X POST http://127.0.0.1:6288/predict \
  -H "Content-Type: application/json" \
  -d '{"inputFile":"<上游 outputFile>","category":"几何","isLastOperator":false}'
```

输入内容版式：`.jsonl` / `.zip`（链路中段，经 inputFile 接续）。

---

##### 图片判型-输出示例

结果写入输出目录 `<OUTPUT_DIR>/img_type_classify_<run_id>/`，`isLastOperator=true` 时整目录收口为 `<run_id>_stage_output.zip`：

| 文件 | 编码 | 说明 |
| --- | --- | --- |
| `records.jsonl` | UTF-8 | 匹配图片一图一行：上游字段 + imageType{match,category,subtype,confidence,reason,taskCategory} |
| `regions/` | PNG | 匹配图片副本（输出自包含，下游直接取图） |
| `review.jsonl` | UTF-8 | 判型低置信/输出非法待复核 + reviewReason |
| `lineage_<run_id>.jsonl` | UTF-8 | 逐图 keep（带 type_confidence）/ skip（大类不一致）/ fail |

> 复核对接口径：`review.jsonl` 每行在完整记录之外带 `reviewReason`（中文，供复核员阅读）与 `code`（小写下划线机器码，如 `low_confidence`、`model_call_failed`，供平台按类型生成复核单）；`/predict` 响应 `data.skipped[]` / `data.failed[]` 条目同样带 `code`（如 `unsupported_suffix`、`pdf_encrypted`、`model_call_failed`）。同一行命中多个条件时只取优先级最高的一个码，无预设条件命中时为 `unclassified`。

`/predict` 成功响应（统一信封）：

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "outputFile": "<OUTPUT_DIR>/img_type_classify_<run_id>/",
    "lineageFile": "<OUTPUT_DIR>/img_type_classify_<run_id>/lineage_<run_id>.jsonl",
    "summary": {...},
    "skipped": [{"name": "...", "reason": "...", "code": "unsupported_suffix"}],
    "failed": [{"name": "...", "reason": "...", "code": "model_call_failed"}]
  }
}
```

主成果行示例（一行）：

```jsonl
{"imageId":"geometry_001",...,"imageType":{"match":true,"category":"几何","subtype":"平面几何图","confidence":0.95,"reason":"图中有半圆与标注点","taskCategory":"几何"}}
```
