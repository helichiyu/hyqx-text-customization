# release · 交付包

- `<算子目录名>.zip` × 11：Docker 构建所需全部内容（解压到同名目录后 compose 构建）
- `docker-compose.yml`：一键起 11 个服务（宿主机端口 6301–6311，共享数据卷 ./op-runtime）
- `前后端对接说明.md`：分工边界、三接口契约、产线编排顺序、调用时序与注意事项（**先读这份**）
- `chain_example.py`：四条产线完整调用示例（compose 起服务后直接跑）
- `docs/`：11 份算子说明书 + 11 份测试指令

快速开始：

```bash
for f in *.zip; do unzip -q "$f" -d "${f%.zip}"; done
docker compose up -d --build
python chain_example.py meta   # 另有 lay / fml / img [几何|统计|表格|示意]
```
