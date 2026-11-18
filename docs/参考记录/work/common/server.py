"""统一 HTTP 壳：POST /predict?detection=PTt_xxx（multipart 文件流）+ GET /health。

实现规范（docs/预训练文本算子开发规范-V1.0.md）：
- 第 3 章 传输：multipart 文件流；血缘归系统，本壳不实现任何血缘/工作区/上传登记逻辑
- 第 4 章 外壳：{code, msg, data:[{fieldName, tags, action, ...业务字段}]}；
          HTTP 状态码只表达传输层（200/400/413/404/500），业务成败看 code
- 第 5 章 参数：form 字段 param_xxx（中文键原值），与 default_params 合并（请求优先）
- 第 6 章 上限：输入 ≤10MB、响应 ≤50MB（环境变量 MAX_INPUT_MB / MAX_RESPONSE_MB 可覆盖），
          超限 413 快速失败
- 第 7/8 章 资源文件：fingerprint_library / lexicon / dictionary / topic_table 以
          文件字段传入，字节交由处理器
- 第 11 章 性能：orjson 可选加速；多 worker 由 Dockerfile 内 gunicorn 承担
- 规范 3.4 认证拦截：common.auth_guard 在两种形态与降级服务统一安装，算子不感知

算子接入方式：inference.py 中 `app = create_app(算子实例)` 即可。
"""

import argparse
import json
import os
from typing import Optional

from common.auth_guard import (
    docs_off_kwargs,
    install_auth,
    is_whitelisted,
    token_from,
    verify,
)
from common.operator_base import Operator, OperatorContext, OperatorOutput

PARAM_PREFIX = "param_"
RESOURCE_FILE_FIELDS = ("fingerprint_library", "lexicon", "dictionary", "topic_table")

DEFAULT_MAX_INPUT_MB = 10
DEFAULT_MAX_RESPONSE_MB = 50


def _max_input_bytes() -> int:
    return int(os.getenv("MAX_INPUT_MB", str(DEFAULT_MAX_INPUT_MB))) * 1024 * 1024


def _max_response_bytes() -> int:
    return int(os.getenv("MAX_RESPONSE_MB", str(DEFAULT_MAX_RESPONSE_MB))) * 1024 * 1024


def _dumps(payload: dict) -> bytes:
    """序列化（orjson 优先，规范 11.2）。"""
    try:
        import orjson

        return orjson.dumps(payload)
    except ImportError:
        return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _envelope(code: int, msg: str, data: Optional[list] = None, **extras) -> dict:
    body = {"code": code, "msg": msg}
    if data is not None:
        body["data"] = data
    body.update(extras)
    return body


def _merge_params(operator: Operator, request_params: dict) -> dict:
    merged = dict(operator.default_params)
    merged.update(request_params)
    return merged


# --------------------------------------------------------------------------
# FastAPI 主实现
# --------------------------------------------------------------------------

async def _run_predict(operator: Operator, request, detection: str):
    """单算子 /predict 的完整处理管线（单算子服务与算子池共用）。"""
    from fastapi.responses import Response

    form = await request.form()
    upload = form.get("file")
    if upload is None or not hasattr(upload, "read"):
        return Response(
            content=_dumps(_envelope(1, "PARAM_INVALID: 缺少必填文件字段 file")),
            status_code=400,
            media_type="application/json",
        )
    data = await upload.read()
    if not data:
        return Response(
            content=_dumps(_envelope(1, "FILE_EMPTY: 上传文件为空")),
            status_code=400,
            media_type="application/json",
        )
    if len(data) > _max_input_bytes():
        limit = os.getenv("MAX_INPUT_MB", str(DEFAULT_MAX_INPUT_MB))
        return Response(
            content=_dumps(_envelope(1, f"SIZE_EXCEEDED: 输入超过 {limit}MB 上限")),
            status_code=413,
            media_type="application/json",
        )

    request_params = {
        key[len(PARAM_PREFIX):]: value for key, value in form.items()
        if isinstance(value, str) and key.startswith(PARAM_PREFIX)
    }
    resources = {}
    for field in RESOURCE_FILE_FIELDS:
        item = form.get(field)
        if item is not None and hasattr(item, "read"):
            resources[field] = await item.read()

    from common.text_records import parse_text_records
    records = parse_text_records(data, upload.filename or "")

    from starlette.concurrency import run_in_threadpool
    context = OperatorContext(raw=data, filename=upload.filename or "")
    try:
        output: OperatorOutput = await run_in_threadpool(
            operator.process, records, _merge_params(operator, request_params),
            resources or None, context,
        )
    except Exception as exc:  # noqa: BLE001 - 整批异常收敛为 code=1
        return Response(
            content=_dumps(_envelope(1, f"INTERNAL_ERROR: {exc}")),
            media_type="application/json",
        )

    body = _envelope(0, "success", [r.to_dict() for r in output.results], **output.extras)
    payload = _dumps(body)
    if len(payload) > _max_response_bytes():
        return Response(
            content=_dumps(
                _envelope(1, "SIZE_EXCEEDED: 响应超过上限，请分批调用（建议单批 ≤500 条）")
            ),
            status_code=413,
            media_type="application/json",
        )
    return Response(content=payload, media_type="application/json")


def create_app(operator: Operator):
    """为一个算子实例构建 FastAPI 应用（一算子一服务形态）。"""
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse, Response

    app = FastAPI(
        title=f"{operator.detection} 服务",
        description=f"{operator.name}（{operator.tool_type}）- 预训练文本产线算子",
        version=operator.version,
        **docs_off_kwargs(),   # 认证启用时关闭文档端点（规范 3.4）
    )
    install_auth(app)

    @app.get("/health")
    async def health():
        return JSONResponse(
            {"status": "healthy", "service": operator.detection, "version": operator.version}
        )

    @app.post("/predict")
    async def predict(request: Request):
        detection = request.query_params.get("detection", "")
        if not detection:
            return Response(
                content=_dumps(_envelope(1, "PARAM_INVALID: 缺少 query 参数 detection")),
                status_code=400,
                media_type="application/json",
            )
        if detection != operator.detection:
            return Response(
                content=_dumps(
                    _envelope(
                        1,
                        f"PARAM_INVALID: detection 不匹配（本服务只承载 {operator.detection}，收到 {detection}）",
                    )
                ),
                status_code=400,
                media_type="application/json",
            )
        return await _run_predict(operator, request, detection)

    return app


def create_pool_app(registry: dict):
    """算子池形态：一个 FastAPI 应用承载多个算子，按 detection 路由（规范 2.3）。

    registry: {detection: Operator 实例}。与单算子服务共用同一条 /predict 管线，
    后端感知不到形态差异（仍然只看 URL + detection）。
    """
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse, Response

    app = FastAPI(
        title="预训练文本产线算子池",
        description=f"承载 {len(registry)} 个算子，POST /predict?detection=PTt_xxx 路由",
        version="1.0.0",
        **docs_off_kwargs(),   # 认证启用时关闭文档端点（规范 3.4）
    )
    install_auth(app)

    @app.get("/health")
    async def health():
        return JSONResponse({
            "status": "healthy",
            "service": "pretrain-text-operator-pool",
            "operators": len(registry),
            "detections": sorted(registry.keys()),
        })

    @app.post("/predict")
    async def predict(request: Request):
        detection = request.query_params.get("detection", "")
        if not detection:
            return Response(
                content=_dumps(_envelope(1, "PARAM_INVALID: 缺少 query 参数 detection")),
                status_code=400,
                media_type="application/json",
            )
        operator = registry.get(detection)
        if operator is None:
            return Response(
                content=_dumps(_envelope(
                    1,
                    f"PARAM_INVALID: 未知算子 {detection}（本池承载 {len(registry)} 个算子，"
                    f"可用: {', '.join(sorted(registry)[:8])}{'...' if len(registry) > 8 else ''}）",
                )),
                status_code=400,
                media_type="application/json",
            )
        return await _run_predict(operator, request, detection)

    return app


# --------------------------------------------------------------------------
# 无 FastAPI 时的标准库降级服务（规范第 9 章：参照示例算子的降级设计）
# --------------------------------------------------------------------------

def run_basic_server(operator: Operator, host: str, port: int):
    import base64
    from http.server import HTTPServer, BaseHTTPRequestHandler

    class OperatorHandler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            print(f"[HTTP] {self.address_string()} - {fmt % args}")

        def _send(self, payload: dict, status: int = 200):
            body = _dumps(payload)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _auth_ok(self) -> bool:
            """认证拦截（规范 3.4）：白名单外缺令牌 401、不符 403。"""
            if is_whitelisted(self.path.split("?")[0]):
                return True
            ok, status, msg = verify(token_from(self.headers))
            if not ok:
                self._send(_envelope(1, msg), status)
                return False
            return True

        def do_GET(self):
            if not self._auth_ok():
                return
            if self.path == "/health":
                self._send({"status": "healthy", "service": operator.detection})
            else:
                self._send(_envelope(1, "未找到接口"), 404)

        def do_POST(self):
            if not self._auth_ok():
                return
            if not self.path.startswith("/predict"):
                self._send(_envelope(1, "未找到接口"), 404)
                return
            if f"detection={operator.detection}" not in self.path:
                self._send(_envelope(1, f"PARAM_INVALID: detection 不匹配（应为 {operator.detection}）"), 400)
                return

            length = int(self.headers.get("Content-Length", 0))
            post = self.rfile.read(length)
            content_type = self.headers.get("Content-Type", "")

            fields: dict = {}
            resources: dict = {}
            filename = "upload.bin"
            file_bytes = b""
            if "multipart/form-data" in content_type:
                boundary = content_type.split("boundary=")[-1].encode()
                for part in post.split(b"--" + boundary):
                    if b'name="' not in part:
                        continue
                    header, _, content = part.partition(b"\r\n\r\n")
                    header_text = header.decode("utf-8", "replace")
                    content = content.rstrip(b"\r\n")
                    name_start = header_text.index('name="') + 6
                    name_end = header_text.index('"', name_start)
                    name = header_text[name_start:name_end]
                    if b'filename="' in header:
                        fn_start = header_text.index('filename="') + 10
                        fn_end = header_text.index('"', fn_start)
                        if name == "file":
                            filename = header_text[fn_start:fn_end] or filename
                            file_bytes = content
                        elif name in RESOURCE_FILE_FIELDS:
                            resources[name] = content   # 指纹库/词库/词典/主题表
                    else:
                        fields[name] = content.decode("utf-8", "replace")
            else:
                try:
                    data = json.loads(post)
                    filename = str(data.get("file_id", filename))
                    file_bytes = base64.b64decode(data.get("content", ""))
                    fields = data.get("params", {})
                except Exception:
                    self._send(_envelope(1, "无效的请求格式"), 400)
                    return

            if not file_bytes:
                self._send(_envelope(1, "FILE_EMPTY: 上传文件为空"), 400)
                return
            if len(file_bytes) > _max_input_bytes():
                self._send(_envelope(1, "SIZE_EXCEEDED: 输入超过上限"), 413)
                return

            from common.text_records import parse_text_records
            records = parse_text_records(file_bytes, filename)
            request_params = {k[len(PARAM_PREFIX):]: v for k, v in fields.items() if k.startswith(PARAM_PREFIX)}
            context = OperatorContext(raw=file_bytes, filename=filename)
            try:
                output = operator.process(records, _merge_params(operator, request_params), resources or None, context)
            except Exception as exc:  # noqa: BLE001
                self._send(_envelope(1, f"INTERNAL_ERROR: {exc}"))
                return

            payload = _envelope(0, "success", [r.to_dict() for r in output.results], **output.extras)
            if len(_dumps(payload)) > _max_response_bytes():
                self._send(_envelope(1, "SIZE_EXCEEDED: 响应超过上限，请分批调用"), 413)
                return
            self._send(payload)

    server = HTTPServer((host, port), OperatorHandler)
    print(f"[INFO] 基础HTTP服务启动: http://{host}:{port}")
    print(f"[INFO] 标准接口: POST http://{host}:{port}/predict?detection={operator.detection}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] 服务关闭")
        server.shutdown()


# --------------------------------------------------------------------------
# 服务入口（inference.py 调用）
# --------------------------------------------------------------------------

def _load_config(config_path: str) -> dict:
    if not os.path.exists(config_path):
        return {}
    try:
        import yaml

        with open(config_path, "r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
    except ImportError:
        print("[WARN] 未安装 PyYAML，使用默认配置")
        return {}
    except Exception as exc:
        print(f"[WARN] 加载配置失败: {exc}")
        return {}


def run_service(operator: Operator, default_port: int = 6300) -> None:
    """命令行入口：python inference.py [--host 0.0.0.0] [--port 63xx] [--config configs/config.yaml]

    生产部署用镜像内 gunicorn 多 worker（见各算子 Dockerfile），此处为单进程开发模式。
    """
    parser = argparse.ArgumentParser(description=f"{operator.detection} 推理服务")
    parser.add_argument("--config", "-c", default="configs/config.yaml")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", "-p", type=int, default=None)
    args = parser.parse_args()

    config = _load_config(args.config)
    app_cfg = config.get("app", {})
    limits = config.get("limits", {})
    if limits.get("max_input_mb"):
        os.environ.setdefault("MAX_INPUT_MB", str(limits["max_input_mb"]))
    if limits.get("max_response_mb"):
        os.environ.setdefault("MAX_RESPONSE_MB", str(limits["max_response_mb"]))

    host = args.host or app_cfg.get("host", "0.0.0.0")
    port = args.port or int(app_cfg.get("port", default_port))

    try:
        import uvicorn

        uvicorn.run(create_app(operator), host=host, port=port)
    except ImportError:
        run_basic_server(operator, host, port)
