"""统一认证拦截层（平台 → 算子服务，升级要求第三节）。

所有对外请求必须携带令牌；服务端只保存令牌的 SHA-256 摘要。
本模块由共享服务外壳（inference.py）统一安装，算子核心代码不感知。

约定：
- 请求头：``X-Token``（兼容 ``token``）
- 生产配置：``AUTH_TOKEN_SHA256``，支持空格或逗号分隔多个摘要（多调用方/令牌轮换）
- 本地联调：可临时使用 ``AUTH_TOKEN`` 明文，摘要变量优先
- ``/health``、``/healthz``（含任意以 ``/healthz`` 结尾的探针路径）白名单放行
- 启用认证后自动关闭 ``/docs``、``/redoc``、``/openapi.json``
- ``AUTH_DISABLED=1`` 显式关闭认证（仅限测试/本地，生产禁止）
- 比对使用 ``secrets.compare_digest`` 防时序侧信道；不使用 MD5

K8s 注入示例（compose 不会自动读 .env，Pod 环境变量必须显式注入）：

    env:
    - name: AUTH_TOKEN_SHA256
      value: <sha256-digest>        # 或 valueFrom.secretKeyRef
"""

from __future__ import annotations

import hashlib
import os
import secrets

TOKEN_HEADERS = ("x-token", "token")
DIGEST_ENV = "AUTH_TOKEN_SHA256"
PLAIN_ENV = "AUTH_TOKEN"
WHITELIST_ENV = "AUTH_WHITELIST_PATHS"
DISABLE_ENV = "AUTH_DISABLED"
DEFAULT_WHITELIST_PATHS = ("/health", "/healthz")

MISSING = (401, "AUTH_MISSING: 缺少访问令牌（请求头 X-Token）")
INVALID = (403, "AUTH_INVALID: 令牌校验失败")


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def auth_disabled() -> bool:
    """AUTH_DISABLED=1/true/yes 时显式关闭认证（仅测试/本地）。"""
    return os.getenv(DISABLE_ENV, "").strip().lower() in ("1", "true", "yes")


def expected_digests() -> list[str]:
    """解析已配置的令牌摘要；未配置返回空列表（关闭拦截）。"""
    raw = os.getenv(DIGEST_ENV, "").strip()
    if not raw:
        plain = os.getenv(PLAIN_ENV, "").strip()
        raw = _digest(plain) if plain else ""
    return [item for item in raw.replace(",", " ").split() if item]


def auth_enabled() -> bool:
    return bool(expected_digests()) and not auth_disabled()


def token_from(headers) -> str | None:
    """按 X-Token、token 的顺序读取令牌。"""
    for name in TOKEN_HEADERS:
        value = (headers.get(name) or "").strip()
        if value:
            return value
    return None


def verify(token: str | None) -> tuple[bool, int, str]:
    """校验令牌，返回 ``(ok, status, message)``。未配置令牌时直接放行。"""
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
    # 放行任意以 /healthz 结尾的探针路径（如多算子形态的 /<tag>/healthz）。
    return normalized.endswith("/healthz")


def docs_off_kwargs() -> dict:
    """认证启用时关闭 FastAPI 自动文档端点。"""
    if auth_enabled():
        return {"docs_url": None, "redoc_url": None, "openapi_url": None}
    return {}


def install_auth(app) -> bool:
    """为 FastAPI 应用安装认证中间件；未配置令牌时跳过并告警。"""
    if auth_disabled():
        print(f"[WARN] {DISABLE_ENV} 已设置，认证拦截被显式关闭（仅限测试/本地，生产禁止）")
        return False
    if not expected_digests():
        print(f"[WARN] 未设置 {DIGEST_ENV}/{PLAIN_ENV}，认证拦截未启用"
              "（生产部署必须注入令牌，见升级要求 3.4）")
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

    print(f"[AUTH] 认证拦截已启用（白名单: {', '.join(sorted(whitelist_paths()))}；"
          "文档端点已关闭）")
    return True
