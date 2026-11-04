# 图片判型（图文融合）

环节① 图片接入与判型 · 视觉大模型（判型）。链路第 2 环：接 img_region_locate 产物；输出供 img_struct_describe 接续。

## 包结构

```text
img_type_classify/                       ← 本目录（算法实现）
├── operator.py              算子核心：run(input_dir, output_dir, params, log) -> dict
├── configs/config.py        阈值与枚举（集中可审计）
├── configs/prompts.py       Prompt 全文（凡调模型的算子）
├── utils/                   外壳与公共能力副本（vendor，包自包含）
├── dataset/sample/          样本（上游真实产物）
└── tests/                   离线单元测试（mock 模型调用，不联网）
```

包根（上一级）另有：`inference.py`（三接口外壳）、`map.json`（算子名）、`requirements.txt`
（版本锁定：fastapi, uvicorn, python-multipart, starlette, pydantic, requests）、`Dockerfile`、
`img_type_classify-算子说明书.md`、`img_type_classify-测试指令.md`。

## 快速运行

```bash
python -m pip install -r ../requirements.txt     # 在包根执行则去掉 ../
python -m uvicorn inference:app --host 0.0.0.0 --port 6288   # 在包根执行
python -m pytest img_type_classify/tests -q                  # 离线单测
```

完整验收步骤（healthz / uploadFile / predict / 负例 / 产物校验）见包根
`img_type_classify-测试指令.md`；技术方案与字段口径见 `img_type_classify-算子说明书.md`。
