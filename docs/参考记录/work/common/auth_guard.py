"""统一认证拦截层（规范 3.4；会议纪要·平台认证拦截解决方案）。

供给平台上的服务直接暴露会被安全扫描判定为漏洞，因此在容器统一入口
拦截所有对外请求：请求头携带令牌，与服务端配置的令牌摘要比对——
缺失 401、不符 403、通过放行。拦截层由 common.server 的两种形态
（单算子 / 算子池）统一安装，算子代码不感知（一个模块保护全部算子）。

令牌约定（对应纪要"加密传输、加密存储"）：
- 传输：调用方在请求头 X-Token 携带令牌原文（兼容 token 头）；
  链路加密由网关/ingress TLS 承担，容器内为 HTTP
- 存储：服务端环境变量只保存令牌的 SHA-256 摘要（AUTH_TOKEN_SHA256；
  多调用方各发一个令牌时用空格/逗号分隔多个摘要），配置泄露也拿不到
  原文。联调可用明文变量 AUTH_TOKEN，摘要变量优先
- 比对用 secrets.compare_digest 防时序侧信道；不采用 MD5（已不安全），
  SHA-256 摘要同为"加密传输存储"口径且强度更高
- /health 白名单放行（K8s 探针与 Docker HEALTHCHECK 不带令牌）
- 认证启用时同步关闭 /docs /redoc /openapi.json（避免扫描出接口文档暴露）

K8S 注入示例：
  kubectl create secret generic op-auth --from-literal=token=<令牌>
  容器环境变量 AUTH_TOKEN 通过 secretKeyRef 引用（或直接注入摘要变量）
"""

from __future__ import annotations

import hashlib
import os
import secrets

TOKEN_HEADERS = ("x-token", "token")   # 令牌请求头（大小写不敏感），X-Token 优先
DIGEST_ENV = "AUTH_TOKEN_SHA256"       # 令牌 SHA-256 摘要（生产推荐，支持多个）
PLAIN_ENV = "AUTH_TOKEN"               # 令牌明文（联调便利，摘要变量优先）
WHITELIST_PATHS = {"/health"}          # 探针/健康检查放行

MISSING = (401, "AUTH_MISSING: 缺少访问令牌（请求头 X-Token）")
INVALID = (403, "AUTH_INVALID: 令牌校验失败")


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def expected_digests() -> list:
    """解析已配置的令牌摘要列表；未配置返回 []（拦截关闭）。"""
    raw = os.getenv(DIGEST_ENV, "").strip()
    if not raw:
        plain = os.getenv(PLAIN_ENV, "").strip()
        raw = _digest(plain) if plain else ""
    return [item for item in raw.replace(",", " ").split() if item] if raw else []


def auth_enabled() -> bool:
    return bool(expected_digests())


def token_from(headers) -> "str | None":
    """按 TOKEN_HEADERS 顺序取令牌。headers 需大小写不敏感取值
    （starlette Headers 与 http.client HTTPMessage 均满足）。"""
    for name in TOKEN_HEADERS:
        value = (headers.get(name) or "").strip()
        if value:
            return value
    return None


def verify(token: "str | None") -> tuple:
    """校验令牌，返回 (ok, status, msg)。未配置令牌时直接放行。"""
    digests = expected_digests()
    if not digests:
        return True, 0, ""
    if not token:
        return False, *MISSING
    actual = _digest(token)
    for expected in digests:
        if secrets.compare_digest(actual, expected):
            return True, 0, ""
    return False, *INVALID


def is_whitelisted(path: str) -> bool:
    """白名单路径判断（忽略尾部斜杠；query 由调用方先行剥离）。"""
    normalized = path.rstrip("/") or "/"
    return normalized in WHITELIST_PATHS


def docs_off_kwargs() -> dict:
    """认证启用时返回关闭文档端点的 FastAPI 构造参数。"""
    if auth_enabled():
        return {"docs_url": None, "redoc_url": None, "openapi_url": None}
    return {}


def install_auth(app) -> bool:
    """给 FastAPI 应用安装认证拦截中间件；未配置令牌时跳过并告警。"""
    if not auth_enabled():
        print(f"[WARN] 未设置 {DIGEST_ENV}/{PLAIN_ENV}，认证拦截未启用"
              f"（生产部署必须注入令牌，见规范 3.4）")
        return False

    from fastapi.responses import JSONResponse  # 与 common.server 一致：fastapi 可选

    @app.middleware("http")
    async def _auth_interceptor(request, call_next):
        if is_whitelisted(request.url.path):
            return await call_next(request)
        ok, status, msg = verify(token_from(request.headers))
        if not ok:
            return JSONResponse(content={"code": 1, "msg": msg}, status_code=status)
        return await call_next(request)

    print(f"[AUTH] 认证拦截已启用（白名单: {', '.join(sorted(WHITELIST_PATHS))}；"
          f"文档端点已关闭）")
    return True
