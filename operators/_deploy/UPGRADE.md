# op-custom-text v1.0.0 升级说明

> 依据《升级要求.md》（docs/参考记录/）完成的三项改造：入站认证拦截、出站切换 IDG/磐智模型网关、部署规范对齐。
> 升级前快照备份：`op-custom-text-docker-v1.0.0-backup.zip`（回滚直接用旧包 + 旧清单）。

## 变更内容

### 1. 入站认证（平台 → 本服务）

- 每个算子进程安装 `auth_guard` 中间件（算子根目录 `auth_guard.py`，与 `inference.py` 同级）。
- 请求头 `X-Token`（兼容 `token`）；服务端只配 SHA-256 摘要 `AUTH_TOKEN_SHA256`（空格/逗号分隔支持多调用方与轮换）。
- 缺令牌 401 `{"code":1,"msg":"AUTH_MISSING..."}`，令牌不符 403；`/health`、`/healthz`（含 `/<算子>/healthz`）白名单放行。
- 认证启用后 `/docs`、`/redoc`、`/openapi.json` 自动关闭。
- `AUTH_DISABLED=1` 显式关闭（仅限测试/本地）；未配置令牌时打印 `[WARN]` 并自动关闭认证——**平台侧未配 X-Token 前不要注入摘要，否则 /predict 全部 401**。

### 2. 出站模型调用（本服务 → IDG/磐智网关）

- 默认 `MODEL_PROVIDER=idg`：网关 `http://10.252.92.98:9050`，APPID+APPKEY 签名（`appKey`/`X-Server-Param`/`X-CurTime`/`X-CheckSum`），模型按 PATH 区分。
- 本产线模型映射：文本 `Qwen3.5-9B` → `/Qwen3.5-9B`（带 `enable_thinking:false`）；视觉 `qwen3-vl-8b-instruct` → `/qwen3-vl-8b-instruct`。
- 响应校验 `X-Code` 为空或 `1000000`、`X-IsSync` 非 `false`；429/5xx 与网络错误重试（默认 2 次），4xx/网关拒绝不重试。
- 回退：`MODEL_PROVIDER=siliconflow` + `SILICONFLOW_API_KEY` 切回硅基流动（OpenAI 兼容）。
- 凭据全部走环境变量，代码与镜像内无任何密钥。

### 3. 部署规范

- 镜像 `op-custom-text:1.0.0`（全小写短横线 + 版本 tag；改代码必须换 tag）。
- compose 不再挂载任何卷：运行期文件只写容器内 `/data`（INPUT_DIR/OUTPUT_DIR），随容器删除回收；K8s 侧请配 `ephemeral-storage` 限额。
- 健康检查固定 `/healthz`（白名单内）；compose 日志轮转 50MB×3。
- 非固定环境变量在 K8s Deployment `env:` 段按 `- name:/value:` 追加，改完滚动重启生效。

## 环境变量速查

| 变量 | 默认 | 说明 |
|---|---|---|
| `MODEL_PROVIDER` | `idg` | 模型后端：`idg` / `siliconflow` |
| `MODEL_GATEWAY_BASE_URL` | `http://10.252.92.98:9050` | 网关地址 |
| `MODEL_APP_ID` / `MODEL_APP_KEY` | `audioasr` / 无 | 网关凭据；APPKEY 必须注入，建议 Secret |
| `MODEL_GATEWAY_TIMEOUT_SECONDS` | `300` | 网关调用超时 |
| `MODEL_GATEWAY_RETRIES` | `2` | 重试次数 |
| `TEXT_MODEL` / `TEXT_MODEL_PATH` | `Qwen3.5-9B` / `/Qwen3.5-9B` | 文本模型与 PATH（逐字） |
| `VISION_MODEL` / `VISION_MODEL_PATH` | `qwen3-vl-8b-instruct` / `/qwen3-vl-8b-instruct` | 视觉模型与 PATH（逐字） |
| `SILICONFLOW_API_KEY` | 空 | 回退后端必填 |
| `AUTH_TOKEN_SHA256` | 空 | 入站令牌摘要（生产注入） |
| `AUTH_TOKEN` | 空 | 令牌明文（仅本地联调，摘要优先） |
| `AUTH_DISABLED` | 空 | `=1` 显式关闭认证（仅测试/本地） |
| `AUTH_WHITELIST_PATHS` | `/health,/healthz` | 白名单覆盖 |

## 验收要点（已通过项见 ✓）

- ✓ `/healthz` 无令牌 200；业务接口无令牌 401、错令牌 403、正确令牌 200（本地 TestClient 冒烟）
- ✓ 认证启用后 `/docs`、`/openapi.json` 不可达（无令牌 401、带令牌 404）
- ✓ 网关签名头（appKey/X-Server-Param/X-CurTime/X-CheckSum）经 mock 网关逐字段校验；`enable_thinking:false` 仅文本；`X-Code`/`X-IsSync` 校验生效
- ✓ 交付清单无 volumes / volumeMounts
- ☐ 容器内到真实网关 `http://10.252.92.98:9050` 的连通性与两个模型的真实调用（需部署环境验证）
- ☐ K8s env 注入后滚动重启生效核对
