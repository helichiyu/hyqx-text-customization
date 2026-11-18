# PTt_extract_xml_body XML抽出正文

- **工具类型**：规则型　|　**所属大阶段**：清洗·正文　|　**是否可跳过**：是（可选-必填1个）
- **主表编号**：#4

## 功能

接收 XML 文档并提取正文，解析文档结构，去除标记符号，仅保留正文文字内容

## 接口

```
POST /predict?detection=PTt_extract_xml_body
Content-Type: multipart/form-data
  file: 待处理文件
  param_正文提取范围: 全文（默认）
  param_标签过滤: 启用（默认）
  param_属性过滤: 启用（默认）
```

完整 schema 见 `map.json`。

## 命令

```bash
python tests/test_network.py
python inference.py --port 6303
docker build -f PTt_extract_xml_body/Dockerfile -t ptt_extract_xml_body:1.0.0 .
```

## 吞吐画像（联调前补实测）

待测。

## 变更记录

| 版本 | 日期 | 说明 |
| --- | --- | --- |
| 1.0.0 | 2026-10-25 | 批次1 迁移开发 |
