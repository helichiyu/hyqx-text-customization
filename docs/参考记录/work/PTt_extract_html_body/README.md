# PTt_extract_html_body 提取HTML/网页正文

- **工具类型**：规则型　|　**所属大阶段**：清洗·正文　|　**是否可跳过**：是（可选-必填1个）
- **主表编号**：#3（Excel《预训练各模态产线工具分析》文本V4）

## 功能

接收 HTML/网页文档并提取正文，整合标题、段落、列表和表格内容，保留必要的层级关系与阅读顺序。

核心算法：行块分布函数（正文行显著长于导航行，滑窗求行块长度后取密度平台段）+ 两端 UI 残留剔除 + 404/失效页检测。逻辑迁移自 demo 仓库（A 级复用）。

## 接口

```
POST /predict?detection=PTt_extract_html_body
Content-Type: multipart/form-data
  file: 待处理文件（html 整体一条记录；jsonl 每行一条）
```

响应（统一外壳，规范第 4 章）：

```json
{
  "code": 0,
  "msg": "success",
  "data": [
    {"fieldName": "sample_news_001", "tags": [], "action": "keep", "text": "提取的正文..."}
  ]
}
```

错误页/无法解码记录：`tags: ["原始文件-无法解析"]`、`action: "remove"`（主表拦截处理：隔离 → 低质原始隔离区）。

完整 schema 见 `map.json`。

## 命令

```bash
# 单元测试（无需服务依赖）
python tests/test_network.py

# 开发模式启动
python inference.py --port 6301

# 生产镜像（在 pretrain_text/ 根目录构建）
docker build -f PTt_extract_html_body/Dockerfile -t ptt-extract-html-body:1.0.0 .
```

## 参数

主表配置项列无算子侧参数（"--"），`default_params = {}`。

## 吞吐画像（联调前补实测）

- 单副本吞吐：待测（纯规则，预估 >1000 docs/s·2worker）
- 资源峰值：CPU 2 核 / 内存 <200MB / 无 GPU
- 模型加载：无

## 变更记录

| 版本 | 日期 | 说明 |
| --- | --- | --- |
| 1.0.0 | 2026-10-25 | 从 demo 迁移核心逻辑，适配本组契约（文件流 + 统一外壳） |
