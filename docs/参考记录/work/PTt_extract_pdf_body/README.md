# PTt_extract_pdf_body 提取PDF正文

- **工具类型**：小模型　|　**所属大阶段**：清洗·正文　|　**是否可跳过**：是（可选-必填1个）
- **主表编号**：#5

## 功能

接收 PDF 文档并提取正文，输出纯文本内容；扫描版 PDF 需 OCR（OCR 依赖未装时明确报错，不静默输出空文档）

## 接口

```
POST /predict?detection=PTt_extract_pdf_body
Content-Type: multipart/form-data
  file: 待处理文件
  param_页码范围: 全部（默认）
  param_表格提取: 启用（默认）
  param_图片文字提取: 启用（默认）
  param_OCR识别: 启用（默认）
```

完整 schema 见 `map.json`。

## 命令

```bash
python tests/test_network.py
python inference.py --port 6304
docker build -f PTt_extract_pdf_body/Dockerfile -t ptt_extract_pdf_body:1.0.0 .
```

## 吞吐画像（联调前补实测）

待测。

## 变更记录

| 版本 | 日期 | 说明 |
| --- | --- | --- |
| 1.0.0 | 2026-10-25 | 批次1 迁移开发 |
