# oppretrain-cot-pool 模型复用映射

更新日期：2026-11-07

## 原则

只复用 CoT 产线已经确认的模型，不引入 Qwen3.5-9B、GLM-4-32B 等新模型角色。

## 映射

| 算子/能力 | 模型 | 网关 PATH | 请求 model 字段 | 说明 |
|---|---|---|---|---|
| T04/T12 | Qwen3.8-27B | `/data-produce-1` | `Qwen3.8-27B` | 生成类任务 |
| T06 题目筛选 | Qwen3.5-4B | `/data-qwen3.5-4b` | `Qwen3.5-4B` | AI 预填 |
| T07 标注任务编排 | Qwen3.5-4B（可选） | `/data-qwen3.5-4b` | `Qwen3.5-4B` | 默认保留草稿生成；可由平台参数 `draftEnabled=false` 关闭 |
| T08 思维链标注预填 | Qwen3.5-4B | `/data-qwen3.5-4b` | `Qwen3.5-4B` | 与 T06 复用同一模型 |
| T09/T10 | Qwen3.5-4B | `/data-qwen3.5-4b` | `Qwen3.5-4B` | 结构化和事实核查 |
| T13 | Qwen3.5-2B | `/data-qwen35-2b-api` | `Qwen3.5-2B` | 质量评分 |
| T14 交叉评审/仲裁 | Qwen3.8-27B | `/data-produce-1` | `Qwen3.8-27B` | 只在评审/仲裁阶段使用，保证判断质量 |
| T15 | Qwen3-Embedding-0.6B | `/Qwen3-Embedding-0.6B/embeddings` | `Qwen3-Embedding-0.6B` | Embeddings API |

## T14 说明

T14 需要处理跨评审员分歧，属于高判断要求任务，因此复用 T04/T12 的 27B，而不是 4B。它只在存在争议时运行，允许比普通预填更高的时延。

## 仍需确认

- 模型网关文本请求是否全部为 OpenAI Chat Completions 格式；
- `X-Server-Param` 的 capability 是否为 PATH 首段，还是网关另有登记值；
- T06/T08 的 4B 预填字段准确率是否满足正式验收；
- 模型网关从部署服务器是否可达。

## 环境变量补充

T07 默认保留草稿生成能力，使用 Qwen3.5-4B。`common/ai_prefill.py` 中 `cot.annotation-draft` 也会使用 T07 配置，因此 `COT_T07_MODEL` / `COT_T07_MODEL_PATH` 必须填写。若业务明确要求关闭 T07 草稿，应通过平台任务参数 `draftEnabled=false` 操作，不能在算子代码或部署包中默认关闭。
