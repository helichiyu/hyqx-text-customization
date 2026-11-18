# FastAPI 入站认证拦截器

## 作用

认证拦截器解决的是：

```text
平台/后端 → 我方算子服务
```

它不负责调用模型服务器。调用模型服务器使用的是 APPID/APPKEY 或 Bearer API Key，属于另一层认证。

## 认证协议

调用方发送：

```http
X-Token: <原始令牌>
```

也兼容：

```http
token: <原始令牌>
```

服务端只保存 SHA-256 摘要：

```env
AUTH_TOKEN_SHA256=<sha256-digest>
```

支持多个调用方：

```env
AUTH_TOKEN_SHA256=<digest-a> <digest-b>
```

本地联调可临时使用：

```env
AUTH_TOKEN=<原始令牌>
```

健康探针路径可配置：

```env
AUTH_WHITELIST_PATHS=/health,/healthz,/ready
```

未配置时默认放行 `/health`、`/healthz`，并放行任意以 `/healthz` 结尾的算子健康路径。

摘要变量优先。

## 行为

| 场景 | 行为 |
|---|---|
| `/health` | 不需要令牌 |
| 其他接口缺少令牌 | 401 |
| 令牌错误 | 403 |
| 令牌正确 | 放行 |
| 启用认证后的 `/docs` | 关闭 |
| 启用认证后的 `/openapi.json` | 关闭 |

错误响应：

```json
{"code":1,"msg":"AUTH_MISSING: 缺少访问令牌（请求头 X-Token）"}
```

## FastAPI 接入

```python
from fastapi import FastAPI
from auth.auth_guard import docs_off_kwargs, install_auth

app = FastAPI(
    title="Operator Service",
    version="1.0.0",
    **docs_off_kwargs(),
)
install_auth(app)

@app.get("/health")
async def health():
    return {"code": 0, "msg": "success"}
```

文件：

- `auth/auth_guard.py`
- `auth/test_auth_guard.py`
- `auth/fastapi_integration_example.py`

## 生成令牌和摘要

```powershell
python -c "import secrets,hashlib; t=secrets.token_urlsafe(32); print('TOKEN='+t); print('SHA256='+hashlib.sha256(t.encode()).hexdigest())"
```

原始令牌发给调用方，摘要配置到服务端。

## 轮换

1. 生成新令牌和摘要
2. 服务端同时加旧摘要和新摘要
3. 更新调用方
4. 确认调用正常
5. 删除旧摘要
6. 重启容器

## 注意事项

- SHA-256 摘要不可逆，不能从摘要恢复原始令牌
- 令牌是固定共享令牌，不是 JWT、不在线轮换
- 令牌泄露后必须立即轮换
- 请求必须经过 HTTPS/TLS
- `/health` 必须放行，否则容器健康检查会失败
- 平台调用 `/predict`、`/operators`、`/ai/prefill` 等接口时必须加 `X-Token`
