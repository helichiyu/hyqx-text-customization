# 算子模型设计

## 正文抽取与切片

### 正文抽取与切片

#### 正文抽取与切片

##### 基础信息

| 分类 | 字段 | 值 |
| --- | --- | --- |
| 基础信息 | 模型编号 | `meta_clean_slice`（编号起区分作用，平台正式编号于交付前统一分配替换） |
| 基础信息 | 模型名称 | 正文抽取与切片 |
| 基础信息 | 模型版本号 | v1.0.0 |
| 基础信息 | 所属产线 | 文本元信息 · 环节① 文档接入与切片 |
| 基础信息 | 技术形态 | 规则（HTML 解析，不调模型） |
| 基础信息 | 链路位置 | 阶段首算子：凭 uniqueId 取上传素材；输出供 meta_genre_judge 接续 |
| 基础信息 | 输入类型 | 一个 zip 或散文件（HTML/HTM，按文件名升序处理）：网页存档 |
| 基础信息 | 输出类型 | 主成果 records.jsonl（一文档一行，含标题/来源/切片数组）+ 血缘 JSONL；/predict 回 outputFile + lineageFile |
| 基础信息 | 技术栈 | Python 3.12、标准库 HTMLParser（解码与正文抽取）+ 正则；HTTP 层 FastAPI + uvicorn。不引入 BeautifulSoup/lxml、不调大模型 |
| 功能定义 | 模型定义 | 交付说明环节① #1#2#4：抽取正文并清洗 → 正文校验（空白页/导航页/至少 1 段可读文本）→ 长文档按章节→段落切片（单片 ≤2000 字、重叠 200 字、超长段落硬切） |
| 功能定义 | 能力边界 | 只做抽取、校验、切片三件事；新闻体裁校验是环节① #3、由下游 meta_genre_judge 承担；不做正文内容改写、不做语言校验（已确认口径：只校验正文非空） |
| 功能定义 | 适用场景 | 文本元信息产线第一环：把网页 HTML 变成结构化正文切片，供体裁判定与后续事实抽取消费 |
| 输出内容描述 | 内容来源 | 文本全部来自上传 HTML：只抽取与切分，不构造、不改写任何内容 |
| 输出内容描述 | 编码格式 | 全部 JSONL/TXT 产物 UTF-8；图片 PNG；阶段收口 zip |
| 输出内容描述 | 输出内容类型 | records.jsonl（一文档一行：docId / fileName / title / source / textLength / sliceCount / slices[{sliceId,index,text,charCount}]）；lineage_<uniqueId>.jsonl（首行 task_lineage（算子/参数/汇总）；其后逐样本 sample_lineage（keep 带 slices 计数 / skip 带原因）） |

---

##### 技术方案

```text
/uploadFile?uniqueId=<任务id_批次id> 上传 zip（阶段首算子）
   ↓  流式落盘 → 解压到 <INPUT_DIR>/<uniqueId>/（抹平目录层级，只留 basename）
/predict 调用（不带 inputFile，凭 uniqueId 取素材；切片参数固定不可覆盖——交付说明 §八）
   ↓  逐文件（文件名升序）：UTF-8→GB18030 两级解码（HTMLParser 解析）
   ↓  抽取：<title>（回退首个标题）、块级段落与标题标记、锚文本占比
   ↓  正文校验（顺序）：total_chars==0 → 空白页跳过
   ↓                    锚文本占比 >0.6 → 导航页跳过
   ↓                    无 ≥20 字段落 → 无有效段落跳过
   ↓  来源线索：前两段内「来源：xxx」正则捕获（供下游体裁判定）
   ↓  切片：超长段落硬切 → 章节断点（标题且当前 ≥1000 字）→ 段落贪心装片
   ↓        （单片 ≤2000 字；新片带上一片末尾 200 字重叠）
写 records.jsonl（一文档一行：docId/fileName/title/source/textLength/sliceCount/slices[]）
   ↓
写 lineage_<uniqueId>.jsonl（首行 task_lineage，其后逐样本 sample_lineage）
   ↓
isLastOperator=true：整目录收口为 <run_id>_stage_output.zip
```

**切片参数为何固定**：交付说明 §八把切片最大长度 2,000 字、重叠 200 字（10%）列为固定项（本项考虑大模型能力），不开放 /predict 覆盖；本算子 PARAM_DEFAULTS 仅为集中可审计，不作为可调参数对外声明

**两级解码的理由**：网页存档混有 UTF-8 与 GBK 系编码，先按 UTF-8 严格解码、失败回退 GB18030，避免乱码进切片

**导航页阈值 0.6**：锚文本字符占全文字符比例超过 0.6 视为链接为主的导航/列表页（交付说明 §九：链接为主，非正文）；边界情形由后续体裁判定的模型兜底

---

##### 技术实现

| 分类 | 字段 | 值 |
| --- | --- | --- |
| 训练方式 | 不涉及。本算子无训练过程；阈值、枚举、Prompt 全文以集中显式常量实现（configs/config.py、configs/prompts.py），逐项可查、可审计 |
| 基础模型 | 不涉及。无预训练权重、无本地推理；规则与确定性计算实现（纯标准库/PyMuPDF/Pillow）。 |
| 训练数据集 | 不涉及。不使用任何训练语料 |
| 测试数据集 | 包内自带（dataset/sample/）：dataset/sample/ = 5 篇 HTML（2 新闻 + 广告产品页 + 教程页 + 导航页），覆盖通过 4 篇与三类跳过原因；由样本生成脚本确定性生成（_shared_tools/make_samples/）。离线用例 mock 模型调用，联网冒烟用例直连真实 API |

**部署与运行**（完整验收步骤见 `meta_clean_slice-测试指令.md`）：

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
python -m pytest meta_clean_slice/tests -q
```

---

##### 资源要求

| 项目 | 实测 / 说明 |
| --- | --- |
| 实测最小配置 · CPU | 单核可运行（受限并发为线程池，无进程并行） |
| 实测最小配置 · 内存 | 服务本体 + FastAPI 栈 < 200 MB；纯文本处理，无媒体位图峰值 |
| 实测最小配置 · 磁盘 | 镜像装载内容约 1 MB 级（inference.py + 内层包 + 样本）；单次运行产出见输出说明，成果只增不减由平台按 outputFile 管理 |
| 是否需要 GPU | 不需要。无本地权重；模型调用在远端 API |
| 实测数据规模 | 包内样本全量（dataset/sample/ = 5 篇 HTML（2 新闻 + 广告产品页 + 教程页 + 导航页），覆盖通过 4 篇与三类跳过原因），单请求完整跑通全部分支 |
| 是否依赖外部 API | 否：运行期无网络请求 |
| 单次运行耗时 | 5 篇 HTML 全量 < 0.1 s（纯 CPU 解析）；不依赖网络 |
| 辅助模块依赖 | 运行必需：fastapi==0.116.1, uvicorn==0.51.0, python-multipart==0.0.32, starlette==0.47.3, pydantic==2.13.4（与 requirements.txt 一致，版本锁定）；测试依赖：pytest==8.3.4 |

---

##### 训练后的模型性能指标

> 本算子无训练过程，不存在模型性能指标；下表为可复现的验证指标——全部由包内单元测试实际断言或真实 API 冒烟实跑得出，可用测试指令复现。

| 指标 | 数值 | 说明 |
| --- | --- | --- |
| 离线单元测试 | 6 / 6 通过 | 标题抽取、GB18030 解码回退、样本池 5 篇（4 通过 + 导航页跳过）、空白/过短分支、4500 字长文硬切成 3 片且相邻片重叠 200 字、参数校验 |
| 真实链路端到端 | 5 → 4 通过 + 1 跳过 | 样本池全量：导航页跳过原因正确；4 篇记录字段齐全（见 .scratch/chain_meta.py 实跑） |
| 确定性 | 同输入两次运行产物一致 | 纯标准库解析 + 贪心切片，无随机成分；不联网、不调模型 |

##### 执行结果截图

| 项目 | 内容 |
| --- | --- |
| 执行结果截图 | [[执行结果截图:正文抽取与切片（文本元信息）运行实录]] |

图 1　正文抽取与切片（文本元信息）执行结果截图。

---

##### 正文抽取与切片-输入示例

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
| 无算子参数 | 切片 2000/200、空白·导航·段落校验阈值全部固定（configs/config.py 集中常量，交付说明 §八固定项） | — | — |

阶段首算子：不带 inputFile；本算子是产线首环，isLastOperator=false（阶段末由 meta_field_fill 收口）。请求示例：

```bash
curl -X POST http://127.0.0.1:6288/predict \
  -H "Content-Type: application/json" \
  -d '{"uniqueId":"meta001","isLastOperator":false}'
```

输入内容版式：`.html` / `.htm` / `.zip`（zip 内抹平层级，其余后缀在上传白名单层跳过并记录）。

---

##### 正文抽取与切片-输出示例

结果写入输出目录 `<OUTPUT_DIR>/meta_clean_slice_<run_id>/`，`isLastOperator=true` 时整目录收口为 `<run_id>_stage_output.zip`：

| 文件 | 编码 | 说明 |
| --- | --- | --- |
| `records.jsonl` | UTF-8 | 一文档一行：docId / fileName / title / source / textLength / sliceCount / slices[{sliceId,index,text,charCount}] |
| `lineage_<uniqueId>.jsonl` | UTF-8 | 首行 task_lineage（算子/参数/汇总）；其后逐样本 sample_lineage（keep 带 slices 计数 / skip 带原因） |

> 复核对接口径：`/predict` 响应 `data.skipped[]` / `data.failed[]` 条目同样带 `code`（如 `unsupported_suffix`、`pdf_encrypted`、`model_call_failed`）。同一行命中多个条件时只取优先级最高的一个码，无预设条件命中时为 `unclassified`。

`/predict` 成功响应（统一信封）：

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "outputFile": "<OUTPUT_DIR>/meta_clean_slice_<run_id>/",
    "lineageFile": "<OUTPUT_DIR>/meta_clean_slice_<run_id>/lineage_<run_id>.jsonl",
    "summary": {...},
    "skipped": [{"name": "...", "reason": "...", "code": "unsupported_suffix"}],
    "failed": [{"name": "...", "reason": "...", "code": "model_call_failed"}]
  }
}
```

主成果行示例（一行）：

```jsonl
{"docId":"news_001","fileName":"news_001.html","title":"某市地铁3号线通车","source":"某市日报","textLength":843,"sliceCount":1,"slices":[{"sliceId":"news_001-s01","index":1,"text":"6月12日，某市地铁3号线正式通车……","charCount":843}]}
```
