# 文本定制化生产 · 算子交付总览

四条产线（文本元信息 / 复杂版面 / 公式文本 / 图文融合）算法侧共 **11 个算子包**，全部位于本目录。平台侧（前端/后端/素材管理/复核/归集）不在本交付范围内。

每个算子包 = 一个独立可部署服务（FastAPI + uvicorn，统一端口 6288），自带样本、单元测试、算子说明书与测试指令。

## 算子清单

| 目录 | 中文名 | 产线 · 环节 | 技术形态 | 调外部 API |
| --- | --- | --- | --- | --- |
| `meta_clean_slice` | 正文抽取与切片 | 文本元信息 ① | 规则（HTML 解析） | 否 |
| `meta_genre_judge` | 新闻体裁判定 | 文本元信息 ① | 文本大模型 + 规则粗筛 | 是 |
| `meta_fact_extract` | 新闻事实抽取 | 文本元信息 ② | 文本大模型 + 规则合并 | 是 |
| `meta_field_fill` | 元信息三组补全 | 文本元信息 ③（末位） | 文本大模型 + 字段校验 | 是 |
| `lay_page_render` | 版面分页渲染 | 复杂版面 ① | 规则（PyMuPDF） | 否 |
| `lay_page_detect` | 逐页版面检测 | 复杂版面 ②③（末位） | 视觉大模型 + 规则分流 | 是 |
| `fml_formula_locate` | 公式区域定位与裁切 | 公式文本 ① | 规则 + 视觉大模型 grounding | 是 |
| `fml_formula_recognize` | 公式识别与结构化标注 | 公式文本 ②③（末位） | 视觉大模型 + 规则校验 + 文本修复 | 是 |
| `img_region_locate` | 图片区域定位与裁切 | 图文融合 ① | CV/规则 | 否 |
| `img_type_classify` | 图片判型 | 图文融合 ① | 视觉大模型 | 是 |
| `img_struct_describe` | 图文要素与描述生成 | 图文融合 ②③（末位） | 视觉大模型 + 规则回核 | 是 |

模型接入统一走硅基流动（OpenAI 兼容）：视觉 `Qwen/Qwen3-VL-8B-Instruct`，文本 `deepseek-ai/DeepSeek-V3.2`；密钥已内置，`SILICONFLOW_BASE_URL` / `SILICONFLOW_API_KEY` 环境变量可覆盖。

## 链路编排（四条产线）

```text
文本元信息： meta_clean_slice ─→ meta_genre_judge ─→ meta_fact_extract ─→ meta_field_fill ─[收口]
复杂版面：   lay_page_render ──→ lay_page_detect ─────────────────────────────[收口]
公式文本：   fml_formula_locate → fml_formula_recognize ─────────────────────[收口]
图文融合：   img_region_locate → img_type_classify ─→ img_struct_describe ──[收口]
```

- 每条产线内算子按箭头顺序串行；线首凭 `uniqueId` 取素材，线内凭 `inputFile` 接续，线末 `isLastOperator=true` 收口为阶段 zip。
- 复杂版面线末位算子同时承担环节③汇总（失败页清单、复核清单、一页一行数据集）；公式/图文两线末位算子同理。
- 图文融合线的判型算子必须带任务参数 `category`（几何/统计/表格/示意）。

## 三接口契约（所有算子包外壳一致）

| 接口 | 说明 |
| --- | --- |
| `GET /healthz` | 就绪探针，返回算子名（读 map.json） |
| `POST /uploadFile?uniqueId=<任务id_批次id>` | 阶段首上传 zip；流式落盘 ≤2GB；解压抹平层级；同一 uniqueId 重传先清空旧素材 |
| `POST /removeFile?uniqueId=` | 幂等删除输入素材 |
| `POST /predict` | 一次性调用；入参 `{uniqueId?, inputFile?, isLastOperator?, ...算子参数}`；成功回统一信封 `{"code":0,"msg":"success","data":{outputFile, lineageFile, summary, skipped, failed}}`；业务失败 `code=1` + 中文原因（HTTP 仍 200） |

- **路径闸门**：`inputFile` 只放行 `INPUT_DIR`/`OUTPUT_DIR` 之内（含阶段 zip），防任意路径读取。
- **端口/目录**：容器内统一 `PORT=6288`；输入/输出根用 `INPUT_DIR`/`OUTPUT_DIR` 环境变量指定（默认包内 `runtime/`）。
- 每算子 `/predict` 支持的参数、取值范围见各自说明书「-输入示例」。

## 阶段传输说明（平台编排对接要点）

1. **阶段首**（meta_clean_slice / lay_page_render / fml_formula_locate / img_region_locate）：平台 `uploadFile` 上传素材 zip 后，`predict` 传 `{"uniqueId": "..."}`（不带 inputFile）。
2. **链路中段**：`predict` 传上一算子响应的 `data.outputFile`（目录或阶段 zip 均可），即 `{"inputFile": "<上一算子 outputFile>"}`。
3. **产线末位**：`predict` 传 `{"isLastOperator": true, ...}`，响应的 `outputFile` 为 `<run_id>_stage_output.zip`（整目录收口），交复核/归集。
4. **输出目录自包含**：每个算子把下游所需文件（含图片）写入自己的输出目录——下游只依赖 `inputFile` 指向的目录，不回溯更上游。
5. **血缘**：每次 predict 写 `lineage_<run_id>.jsonl`（首行 task_lineage：算子/参数/汇总；其后逐样本 sample_lineage：keep/skip/fail/review + 原因），响应 `data.lineageFile` 直接可取。

## 结果路由（skip / review / failed）

| 去向 | 语义 | 是否阻断 |
| --- | --- | --- |
| `skipped` | 素材不适用（导航页/非新闻/大类不一致/空白页等），记录中文原因 + 机器码 `code` | 不进下游，不阻断同批其它样本 |
| `review.jsonl` | 低置信/冲突/输出非法等，待人工复核（行内带 `reviewReason` 中文原因与 `code` 机器码） | 样本继续下游（数据集行保留，reviewStatus=待复核） |
| `failed` | 处理失败（加密 PDF/模型持续失败/整份 0 公式等），同样带 `code` | 该样本出局，不进下游 |

`code` 为小写下划线机器码（如 `low_confidence`、`model_call_failed`、`category_mismatch`），平台据此决定复核单类型（`triggerCode`），**不要解析中文原因**；中文原因仍保留在 `reason` / `reviewReason` 供人阅读。同一行命中多个条件时按优先级只取一个码，未命中任何预设条件时为 `unclassified`。

冲突不阻断（如时间候选冲突）：进复核由人裁定；系统性错误重跑环节时旧复核单作废由平台侧管理。

## 统一约定（四份交付说明共同口径）

- 模型调用：temperature 0、超时 60s、传输层重试 2 次（最多 3 次）、JSON-only 输出、算子内并发 4–8、输出非法算子内重试 1 次。
- 置信度统一截断 `[0, 0.98]`（模型自评分仅作相对高低，阈值 0.8 待真实样本校准）。
- 阈值/Prompt 全文集中显式（`configs/config.py` / `configs/prompts.py`），逐项可审计；固定项（切片 2000/200、IoU 0.3、上下文 2000 字、重试 2 次）不开放 predict 覆盖。
- 主成果 JSONL 一行一条记录，字段与各交付说明「数据集明细字段」一致；全部产物 UTF-8。

## 交付包结构（每算子一致）

```text
operators/<tag>/
├── inference.py              # 三接口外壳（由 _shared_tools/gen_inference.py 生成，逐算子相同）
├── map.json                  # {"<tag>": "<中文名>"}
├── requirements.txt          # 版本锁定，按算子依赖裁剪
├── Dockerfile                # python:3.12-slim，EXPOSE 6288
├── <tag>-算子说明书.md        # 八节：基础信息/技术方案/技术实现/资源要求/性能指标/截图/输入示例/输出示例
├── <tag>-测试指令.md          # 0 前置 → 起服务 → healthz → upload → predict → 产物校验 → removeFile → 负例 → 单测
└── <tag>/                    # 算法实现（operator.py + configs + utils 副本 + dataset/sample + tests + README）
```

`_shared_tools/` 为开发侧共享基建（外壳生成器、LLM client、样本生成、说明书生成器、全量冒烟），不随算子包部署；算子包内的 `utils/` 是公共能力的 vendored 副本，保证单包自包含。

## 验收入口

```bash
# 全量离线冒烟（外壳契约 + 11 算子单测，约 10 秒，不联网）
python -I operators/_shared_tools/run_all_checks.py

# 追加四条产线真实 API 端到端（需出网，约 5–10 分钟）
python -I operators/_shared_tools/run_all_checks.py --online

# 单算子验收：进入算子目录，按 <tag>-测试指令.md 逐步执行
```

## 已知待确认（不阻塞交付，默认口径已在实现与说明书中标注）

| # | 问题 | 当前默认口径 |
| --- | --- | --- |
| Q1 | 图文融合环节①「区域定位与裁切」的定位语义（交付说明只写「CV/规则，不调模型」） | 整图直通 + 均色边框（拍照黑边/扫描白边）自动裁剪；若甲方指其它语义需给原型或举例后替换 |
| Q2 | 说明书是否必须 docx | 先交 md；需要时用兄弟项目 `md2docx.py` 转换 |
| Q3 | 置信度阈值 0.8 校准 | 模型自评分仅作相对高低；真实样本到位后按分布校准 |
