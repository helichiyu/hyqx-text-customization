# PTt_extract_docx_body 提取DOCX正文

- **工具类型**：规则型　|　**所属大阶段**：清洗·正文　|　**是否可跳过**：是（可选-必填1个）
- **主表编号**：#6

## 功能

接收 Word 文档（.docx）并提取正文（段落+表格+可选超链接），输出纯文本内容

## 接口

```
POST /predict?detection=PTt_extract_docx_body
Content-Type: multipart/form-data
  file: 待处理文件
  param_表格内容: 保留（默认）
  param_批注: 删除（默认）
  param_超链接: 删除（默认）
  param_图片说明文字: 保留（默认）
```

完整 schema 见 `map.json`。

## 命令

```bash
python tests/test_network.py
python inference.py --port 6305
docker build -f PTt_extract_docx_body/Dockerfile -t ptt_extract_docx_body:1.0.0 .
```

## 吞吐画像（联调前补实测）

待测。

## 变更记录

| 版本 | 日期 | 说明 |
| --- | --- | --- |
| 1.0.0 | 2026-10-25 | 批次1 迁移开发 |
