"""算子 HTTP 服务外壳（三接口 + /healthz）。

本文件为**模板**：由 `_shared_tools/gen_inference.py` 原样复制到每个算子包根目录，
算子身份从同目录 `map.json` 的第一个 key 解析，因此所有算子的 inference.py 逐字节相同。

| 接口 | 方法 | 作用 |
| --- | --- | --- |
| `/uploadFile?uniqueId=<id>` | POST | multipart 收 zip 或单文件，流式落盘到 `<INPUT_DIR>/<uniqueId>/`，zip 解压抹平层级 |
| `/removeFile?uniqueId=<id>` | POST | 幂等删除该 uniqueId 登记的上传素材 |
| `/predict` | POST | JSON `{uniqueId?, inputFile?, isLastOperator?, ...算子参数}`，一次性 JSON 响应 |
| `/healthz` | GET | 就绪探针 |

阶段传输约定：

* 阶段首算子（不传 `inputFile`）：输入 = `<INPUT_DIR>/<uniqueId>/`；
* 阶段中间算子（传 `inputFile`）：输入 = 上一算子响应的 `data.outputFile`，经路径闸门校验；
* 阶段末算子（`isLastOperator=true`）：输出目录打包为 `<run_id>_stage_output.zip` 作为 `data.outputFile`；
* 所有响应 `data` 至少含 `outputFile` 与 `lineageFile`。

算子核心契约（`<tag>.operator`）：

* 必须提供 `run(input_dir: Path, output_dir: Path, params: dict, log) -> dict`，返回：
  `records_file`（主成果 JSONL 相对路径，可无）、`summary`（计数汇总）、
  `skipped`/`failed`（跳过/失败清单，元素 `{"name","reason"}`）、`sample_lineage`（逐样本血缘）；
* 可选 `OPERATOR_NAME`（中文名）、`ALLOWED_SUFFIXES`（收件白名单，缺省收全量）、
  `validate_params(params) -> dict`（参数校验/补默认，不合法抛 ValueError，信息用中文）。

环境变量：`INPUT_DIR`、`OUTPUT_DIR`（默认 `<包根>/runtime/input|output`）、`PORT`（默认 6288）。
统一信封 `{"code":0,"msg":"success","data":{...}}`；业务失败 `code=1`，HTTP 仍为 200。
"""

from __future__ import annotations

import importlib
import json
import logging
import os
import re
import shutil
import sys
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Query, Request, UploadFile
from fastapi.responses import JSONResponse

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_map = json.loads((ROOT / "map.json").read_text(encoding="utf-8"))
OPERATOR_TAG = next(iter(_map))
OPERATOR_NAME = _map[OPERATOR_TAG]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger(OPERATOR_TAG)

core = importlib.import_module(f"{OPERATOR_TAG}.operator")

VERSION = "1.0.0"
DEFAULT_PORT = int(os.getenv("PORT", "6288"))

INPUT_DIR = Path(os.getenv("INPUT_DIR", ROOT / "runtime" / "input")).resolve()
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", ROOT / "runtime" / "output")).resolve()

ALLOWED_SUFFIXES = tuple(getattr(core, "ALLOWED_SUFFIXES", (
    ".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".html", ".htm", ".zip",
    ".jsonl", ".json", ".csv", ".txt",
)))

UNIQUE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
UPLOAD_CHUNK_BYTES = 1024 * 1024
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", 2 * 1024 * 1024 * 1024))  # 单包 2 GB
MAX_EXTRACT_BYTES = int(os.getenv("MAX_EXTRACT_BYTES", 10 * 1024 * 1024 * 1024))  # 解压后 10 GB


def _envelope(code: int, msg: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"code": code, "msg": msg, "data": data or {}}


def _fail(msg: str, data: dict[str, Any] | None = None) -> JSONResponse:
    return JSONResponse(_envelope(1, msg, data))


def _run_id() -> str:
    return f"run_{datetime.now().strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}"


def _check_unique_id(unique_id: str) -> str:
    if not UNIQUE_ID_RE.match(unique_id or ""):
        raise ValueError("uniqueId 不合规：仅允许字母数字开头，可含 . _ -，最长 128")
    return unique_id


def _gate_path(raw: str) -> Path:
    """inputFile 路径闸门：必须解析到 INPUT_DIR 或 OUTPUT_DIR 之内。"""

    if not raw or not str(raw).strip():
        raise ValueError("inputFile 不能为空")
    candidate = Path(raw).resolve()
    for root in (INPUT_DIR, OUTPUT_DIR):
        try:
            candidate.relative_to(root)
            return candidate
        except ValueError:
            continue
    raise ValueError(f"inputFile 越界，只允许 {INPUT_DIR} 或 {OUTPUT_DIR} 之下的路径")


def _extract_zip_flat(archive_path: Path, destination: Path) -> tuple[list[str], list[dict[str, str]]]:
    """zip 解压抹平层级（只取 basename，防 zip-slip）；白名单外/重名文件跳过并记录原因。"""

    files: list[str] = []
    skipped: list[dict[str, str]] = []
    total = 0
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            name = Path(member.filename.replace("\\", "/")).name
            if member.is_dir() or not name:
                continue
            reason = code = None
            if Path(name).suffix.lower() not in ALLOWED_SUFFIXES:
                reason, code = "后缀不在收件白名单内，已跳过", "unsupported_suffix"
            elif name in files:
                reason, code = "zip 内重名，已保留第一个", "duplicate_name"
            elif total + member.file_size > MAX_EXTRACT_BYTES:
                raise ValueError(f"zip 解压后总量超过上限 {MAX_EXTRACT_BYTES // (1024 ** 3)} GB")
            if reason:
                skipped.append({"name": name, "reason": reason, "code": code})
                continue
            with (destination / name).open("wb") as sink, archive.open(member) as source:
                shutil.copyfileobj(source, sink, UPLOAD_CHUNK_BYTES)
            total += member.file_size
            files.append(name)
    return files, skipped


def _write_lineage(path: Path, task_lineage: dict[str, Any], sample_lineage: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        f.write(json.dumps({"record_type": "task_lineage", **task_lineage}, ensure_ascii=False) + "\n")
        for row in sample_lineage:
            f.write(json.dumps({"record_type": "sample_lineage", **row}, ensure_ascii=False) + "\n")


def _package_stage(output_dir: Path, run_id: str) -> Path:
    zip_path = OUTPUT_DIR / f"{run_id}_stage_output.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(output_dir.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(output_dir))
    return zip_path


def create_app() -> FastAPI:
    app = FastAPI(title=f"{OPERATOR_TAG} · {OPERATOR_NAME}", version=VERSION)
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    @app.exception_handler(Exception)
    async def _unhandled(_req: Request, exc: Exception) -> JSONResponse:
        return _fail(f"服务内部错误：{type(exc).__name__}: {exc}")

    @app.get("/healthz")
    async def healthz() -> dict[str, Any]:
        return _envelope(0, "success", {
            "operator": OPERATOR_TAG, "name": OPERATOR_NAME,
            "version": VERSION, "status": "ready",
        })

    @app.post("/uploadFile")
    async def upload_file(uniqueId: str = Query(...), file: UploadFile = File(...)) -> JSONResponse:
        try:
            _check_unique_id(uniqueId)
            dest = INPUT_DIR / uniqueId
            dest.mkdir(parents=True, exist_ok=True)
            filename = Path(file.filename or "upload.bin").name
            raw_path = dest / filename
            size = 0
            with raw_path.open("wb") as sink:
                while (chunk := await file.read(UPLOAD_CHUNK_BYTES)):
                    size += len(chunk)
                    if size > MAX_UPLOAD_BYTES:
                        sink.close()
                        raw_path.unlink(missing_ok=True)
                        return _fail(f"上传文件超过上限 {MAX_UPLOAD_BYTES // (1024 ** 3)} GB")
                    sink.write(chunk)
            data: dict[str, Any] = {"uniqueId": uniqueId, "files": [], "skipped": []}
            if filename.lower().endswith(".zip"):
                try:
                    files, skipped = _extract_zip_flat(raw_path, dest)
                except zipfile.BadZipFile:
                    raw_path.unlink(missing_ok=True)
                    return _fail("ZIP 损坏或加密，整批拒绝")
                raw_path.unlink(missing_ok=True)
                data["files"] = files
                data["skipped"] = skipped
            else:
                if Path(filename).suffix.lower() not in ALLOWED_SUFFIXES:
                    raw_path.unlink(missing_ok=True)
                    return _fail(f"后缀 {Path(filename).suffix} 不在收件白名单内")
                data["files"] = [filename]
            return JSONResponse(_envelope(0, "success", data))
        except ValueError as e:
            return _fail(str(e))

    @app.post("/removeFile")
    async def remove_file(uniqueId: str = Query(...)) -> JSONResponse:
        try:
            _check_unique_id(uniqueId)
        except ValueError as e:
            return _fail(str(e))
        dest = INPUT_DIR / uniqueId
        deleted = dest.exists()
        if deleted:
            shutil.rmtree(dest, ignore_errors=True)
        return JSONResponse(_envelope(0, "success", {"uniqueId": uniqueId, "deleted": deleted}))

    @app.post("/predict")
    async def predict(request: Request) -> JSONResponse:
        body = await request.json()
        unique_id = body.pop("uniqueId", None)
        input_file = body.pop("inputFile", None)
        is_last = bool(body.pop("isLastOperator", False))
        params: dict[str, Any] = body

        try:
            if input_file:
                input_dir = _gate_path(input_file)
                if not input_dir.exists():
                    raise ValueError(f"inputFile 不存在：{input_dir}")
            elif unique_id:
                input_dir = INPUT_DIR / _check_unique_id(unique_id)
                if not input_dir.exists():
                    raise ValueError(f"未找到 uniqueId={unique_id} 的上传素材，请先 /uploadFile")
            else:
                raise ValueError("predict 需要 uniqueId（阶段首）或 inputFile（阶段内）")

            if hasattr(core, "validate_params"):
                params = core.validate_params(params)

            run_id = _run_id()
            output_dir = OUTPUT_DIR / f"{OPERATOR_TAG}_{run_id}"
            output_dir.mkdir(parents=True, exist_ok=True)

            started = datetime.now(timezone.utc)
            result = core.run(input_dir, output_dir, params, log=log.info)
            finished = datetime.now(timezone.utc)

            lineage_file = output_dir / f"lineage_{unique_id or run_id}.jsonl"
            _write_lineage(lineage_file, {
                "operator": OPERATOR_TAG, "name": OPERATOR_NAME, "version": VERSION,
                "uniqueId": unique_id, "run_id": run_id, "params": params,
                "started_at": started.isoformat(), "finished_at": finished.isoformat(),
                "summary": result.get("summary", {}),
            }, result.get("sample_lineage", []))

            output_file: Path = output_dir
            if is_last:
                output_file = _package_stage(output_dir, run_id)

            return JSONResponse(_envelope(0, "success", {
                "outputFile": str(output_file),
                "lineageFile": str(lineage_file),
                "summary": result.get("summary", {}),
                "skipped": result.get("skipped", []),
                "failed": result.get("failed", []),
            }))
        except ValueError as e:
            return _fail(str(e))
        except Exception as e:  # 核心异常包装为业务失败，不暴露堆栈
            return _fail(f"算子执行失败：{type(e).__name__}: {e}")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=DEFAULT_PORT)
