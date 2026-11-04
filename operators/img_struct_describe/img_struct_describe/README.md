# 图文要素与描述生成（图文融合）

环节② 要素与结构提取 + 环节③ 描述生成（产线末位） · 视觉大模型（按判型选 4 套 Prompt 之一，一次调用）+ 规则回核。链路第 3 环（末位）：接 img_type_classify 产物；isLastOperator=true 收口。

## 包结构

```text
img_struct_describe/                       ← 本目录（算法实现）
├── operator.py              算子核心：run(input_dir, output_dir, params, log) -> dict
├── configs/config.py        阈值与枚举（集中可审计）
├── configs/prompts.py       Prompt 全文（凡调模型的算子）
├── utils/                   外壳与公共能力副本（vendor，包自包含）
├── dataset/sample/          样本（上游真实产物）
└── tests/                   离线单元测试（mock 模型调用，不联网）
```

包根（上一级）另有：`inference.py`（三接口外壳）、`map.json`（算子名）、`requirements.txt`
（版本锁定：fastapi, uvicorn, python-multipart, starlette, pydantic, requests）、`Dockerfile`、
`img_struct_describe-算子说明书.md`、`img_struct_describe-测试指令.md`。

## 快速运行

```bash
python -m pip install -r ../requirements.txt     # 在包根执行则去掉 ../
python -m uvicorn inference:app --host 0.0.0.0 --port 6288   # 在包根执行
python -m pytest img_struct_describe/tests -q                  # 离线单测
```

完整验收步骤（healthz / uploadFile / predict / 负例 / 产物校验）见包根
`img_struct_describe-测试指令.md`；技术方案与字段口径见 `img_struct_describe-算子说明书.md`。
