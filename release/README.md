# release · 交付包

## 当前交付（v1.1.0，按《升级要求.md》升级）

- `op-custom-text-docker-v1.1.0.zip`：**单容器交付包**（11 算子合并，对外端口 17022，nginx 按 `/<算子名>/` 路由）。
  解压后 `docker compose up -d --build`；包内 `UPGRADE.md` 有变更说明与环境变量速查。
  - 入站认证：`X-Token` + `AUTH_TOKEN_SHA256` 摘要（未注入时认证自动关闭并打 WARN）
  - 出站模型：默认 IDG/磐智网关（`MODEL_PROVIDER=idg`），SiliconFlow 为回退
  - 平台规范：不挂载任何卷、探针 `/healthz`、镜像 `op-custom-text:1.1.0`、日志轮转 50MB×3
- `op-custom-text-docker-v1.0.0-backup.zip`：**v1.0.0 旧版备份**（升级前算子，回滚用，勿删）

## 本地联调（每算子独立端口 6301–6311）

- `docker-compose.yml`：per-port 形态（挂载 ./op-runtime；凭据放 `operators/.env`，不入库）
- `前后端对接说明.md`：分工边界、接口契约、产线编排顺序、调用时序（**先读这份**）
- `chain_example.py`：四条产线完整调用示例
- `docs/`：11 份算子说明书 + 11 份测试指令

```bash
docker compose up -d --build
python chain_example.py meta   # 另有 lay / fml / img [几何|统计|表格|示意]
```
