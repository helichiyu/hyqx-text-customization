"""统一认证拦截层。

所有对外请求必须携带令牌；服务端只保存令牌的 SHA-256 摘要。

约定：
- 请求头：``X-Token``（兼容 ``token``）
- 生产配置：``AUTH_TOKEN_SHA256``，支持空格或逗号分隔多个摘要
- 本地联调：可临时使用 ``AUTH_TOKEN`` 明文，摘要变量优先
- ``/health`` 白名单放行，供 Docker/K8s 探针使用
- 启用认证后自动关闭 ``/docs``、``/redoc``、``/openapi.json``
"""

from __future__ import annotations

import hashlib
import os
import secrets

TOKEN_HEADERS = ("x-token", "token")
DIGEST_ENV = "AUTH_TOKEN_SHA256"
PLAIN_ENV = "AUTH_TOKEN"
WHITELIST_ENV = "AUTH_WHITELIST_PATHS"
DEFAULT_WHITELIST_PATHS = ("/health", "/healthz")

MISSING = (401, "AUTH_MISSING: 缺少访问令牌（请求头 X-Token）")
INVALID = (403, "AUTH_INVALID: 令牌校验失败")


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def expected_digests() -> list[str]:
    """解析已配置的令牌摘要；未配置返回空列表（关闭拦截）。"""
    raw = os.getenv(DIGEST_ENV, "").strip()
    if not raw:
        plain = os.getenv(PLAIN_ENV, "").strip()
        raw = _digest(plain) if plain else ""
    return [item for item in raw.replace(",", " ").split() if item]


def auth_enabled() -> bool:
    return bool(expected_digests())


def token_from(headers) -> str | None:
    """按 X-Token、token 的顺序读取令牌。"""
    for name in TOKEN_HEADERS:
        value = (headers.get(name) or "").strip()
        if value:
            return value
    return None


def verify(token: str | None) -> tuple[bool, int, str]:
    """校验令牌，返回 ``(ok, status, message)``。"""
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


def whitelist_paths() -> set[str]:
    raw = os.getenv(WHITELIST_ENV, "").strip()
    if not raw:
        return set(DEFAULT_WHITELIST_PATHS)
    return {item.strip() for item in raw.replace(",", " ").split()
            if item.strip()}


def is_whitelisted(path: str) -> bool:
    normalized = path.rstrip("/") or "/"
    if normalized in whitelist_paths():
        return True
    # Allow per-operator health probes such as /<tag>/healthz.
    return normalized.endswith("/healthz")


def docs_off_kwargs() -> dict:
    """认证启用时关闭 FastAPI 自动文档端点。"""
    if auth_enabled():
        return {"docs_url": None, "redoc_url": None, "openapi_url": None}
    return {}


def install_auth(app) -> bool:
    """为 FastAPI 应用安装认证中间件；未配置令牌时跳过并告警。"""
    if not auth_enabled():
        print(
            f"[WARN] 未设置 {DIGEST_ENV}/{PLAIN_ENV}，认证拦截未启用"
            "（生产部署必须注入令牌）"
        )
        return False

    from fastapi.responses import JSONResponse

    @app.middleware("http")
    async def _auth_interceptor(request, call_next):
        if is_whitelisted(request.url.path):
            return await call_next(request)
        ok, status, msg = verify(token_from(request.headers))
        if not ok:
            return JSONResponse(content={"code": 1, "msg": msg}, status_code=status)
        return await call_next(request)

    print(
        f"[AUTH] 认证拦截已启用（白名单: {', '.join(sorted(whitelist_paths()))}；"
        "文档端点已关闭）"
    )
    return True
