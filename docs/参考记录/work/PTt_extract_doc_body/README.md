# PTt_extract_doc_body 提取DOC正文

- **工具类型**：规则型　|　**所属大阶段**：清洗·正文　|　**是否可跳过**：是（可选-必填1个）
- **主表编号**：#7

## 功能

接收旧版 Word 文档（.doc）并提取正文：镜像内 LibreOffice headless 转文本

## 接口

```
POST /predict?detection=PTt_extract_doc_body
Content-Type: multipart/form-data
  file: 待处理文件
```

完整 schema 见 `map.json`。

## 命令

```bash
python tests/test_network.py
python inference.py --port 6306
docker build -f PTt_extract_doc_body/Dockerfile -t ptt_extract_doc_body:1.0.0 .
```

## 吞吐画像（联调前补实测）

待测。

## 变更记录

| 版本 | 日期 | 说明 |
| --- | --- | --- |
| 1.0.0 | 2026-10-25 | 批次1 迁移开发 |
