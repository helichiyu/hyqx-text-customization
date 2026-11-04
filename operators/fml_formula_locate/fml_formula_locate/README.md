# 公式区域定位与裁切（公式文本）

环节① 素材接入与定位 · 规则（PDF 渲染）+ 视觉大模型（grounding 定位）。阶段首算子：凭 uniqueId 取上传素材；输出供 fml_formula_recognize 接续。

## 包结构

```text
fml_formula_locate/                       ← 本目录（算法实现）
├── operator.py              算子核心：run(input_dir, output_dir, params, log) -> dict
├── configs/config.py        阈值与枚举（集中可审计）
├── configs/prompts.py       Prompt 全文（凡调模型的算子）
├── utils/                   外壳与公共能力副本（vendor，包自包含）
├── dataset/sample/          样本（formula_sample.pdf）
└── tests/                   离线单元测试（mock 模型调用，不联网）
```

包根（上一级）另有：`inference.py`（三接口外壳）、`map.json`（算子名）、`requirements.txt`
（版本锁定：fastapi, uvicorn, python-multipart, starlette, pydantic, requests, pymupdf, pillow）、`Dockerfile`、
`fml_formula_locate-算子说明书.md`、`fml_formula_locate-测试指令.md`。

## 快速运行

```bash
python -m pip install -r ../requirements.txt     # 在包根执行则去掉 ../
python -m uvicorn inference:app --host 0.0.0.0 --port 6288   # 在包根执行
python -m pytest fml_formula_locate/tests -q                  # 离线单测
```

完整验收步骤（healthz / uploadFile / predict / 负例 / 产物校验）见包根
`fml_formula_locate-测试指令.md`；技术方案与字段口径见 `fml_formula_locate-算子说明书.md`。
