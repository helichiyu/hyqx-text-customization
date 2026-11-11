"""算子 HTTP 服务外壳（三接口 + /healthz）。

本文件为**模板**：由 `_shared_tools/gen_inference.py` 原样复制到每个算子包根目录，
算子身份从同目录 `map.json` 的第一个 key 解析，因此所有算子的 inference.py 逐字节相同。

| 接口 | 方法 | 作用 |
| --- | --- | --- |
| `/uploadFile?uniqueId=<id>` | POST | multipart 收 zip 或单文件，流式落盘到 `<INPUT_DIR>/<uniqueId>/`，zip 解压抹平层级 |
| `/removeFile?uniqueId=<id>` | POST | 幂等删除该 uniqueId 登记的上传素材 |
| `/predict` | POST | JSON `{uniqueId?, inputFile?, isLastOperator?, ...算子参数}`，一次性 JSON 响应 |
| `/healthz` | GET | 就绪探针 |
| `/listFiles?path=<outputFile>` | GET | 列出产物目录（一层）或阶段 zip 内的文件，`{code:0,data:[{name,size}]}` |
| `/downloadFile?path=&name=` | GET | 按名取产物文件原始字节；失败返回非 200 |
| `/progress?runId=<progressKey>` | GET | 读取 `/predict` 落盘的进度 JSON；不存在时 `code=1` |

产物读取接口的平台侧契约见 `platform-hsmty/docs/算子文件接口约定.md`：`path` 是 `/predict` 返回的
`data.outputFile`（目录或阶段 zip），与 `inputFile` 走同一道路径闸门。

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
import mimetypes
import os
import re
import shutil
import sys
import threading
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from starlette.concurrency import run_in_threadpool

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
MAX_EXTRACT_ENTRIES = int(os.getenv("MAX_EXTRACT_ENTRIES", 100 * 1000))  # zip 条目数上限（防 zip 炸弹）
MAX_LIST_ENTRIES = int(os.getenv("MAX_LIST_ENTRIES", 20 * 1000))  # listFiles 返回条目上限


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


def _gate_path(raw: str, label: str = "inputFile", roots: tuple[Path, ...] | None = None) -> Path:
    """路径闸门：必须解析到允许根之内。inputFile 用 INPUT_DIR+OUTPUT_DIR；产物读取只用 OUTPUT_DIR。

    对外只回固定文案，绝对路径写服务端日志（不暴露容器内目录结构）。
    """

    if not raw or not str(raw).strip():
        raise ValueError(f"{label} 不能为空")
    candidate = Path(raw).resolve()
    for root in (roots or (INPUT_DIR, OUTPUT_DIR)):
        try:
            candidate.relative_to(root)
            return candidate
        except ValueError:
            continue
    log.warning("路径闸门拒绝: %s=%s", label, raw)
    raise ValueError(f"{label} 越界，仅允许受控目录之内的路径")


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
            if len(files) + len(skipped) >= MAX_EXTRACT_ENTRIES:
                raise ValueError(f"zip 条目数超过上限 {MAX_EXTRACT_ENTRIES}")
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


# ==================== 产物读取辅助 ====================

#: mimetypes 不认识的扩展名补充（其余交给 mimetypes）
_CONTENT_TYPES = {
    ".json": "application/json",
    ".jsonl": "application/x-ndjson",
    ".csv": "text/csv",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".html": "text/html",
    ".htm": "text/html",
}


def _ok(data: Any) -> JSONResponse:
    """成功信封，允许 data 为数组（_envelope 的 `data or {}` 会把空数组变成空对象）。"""

    return JSONResponse({"code": 0, "msg": "success", "data": data})


def _content_type(name: str) -> str:
    suffix = Path(name).suffix.lower()
    return _CONTENT_TYPES.get(suffix) or mimetypes.guess_type(name)[0] or "application/octet-stream"


def _safe_entry_name(name: str) -> str:
    """downloadFile 条目名闸门：禁止绝对路径与 .. 穿越。"""

    normalized = (name or "").replace("\\", "/").strip()
    if not normalized:
        raise ValueError("name 不能为空")
    if normalized.startswith("/") or any(part in ("..", "") for part in normalized.split("/")):
        raise ValueError("name 不允许为绝对路径或包含 ..")
    return normalized


def _resolve_child(directory: Path, name: str) -> Path:
    """把条目名解析到目录之内，越界拒绝。"""

    child = (directory / name).resolve()
    try:
        child.relative_to(directory.resolve())
    except ValueError:
        raise ValueError("name 越界，只允许目录内的文件") from None
    return child


def _zip_entry_name(info: zipfile.ZipInfo) -> str:
    return info.filename.replace("\\", "/")


def _find_zip_entry(archive: zipfile.ZipFile, name: str) -> zipfile.ZipInfo | None:
    for info in archive.infolist():
        if not info.is_dir() and _zip_entry_name(info) == name:
            return info
    return None


def _iter_zip_entry(zip_path: Path, name: str):
    """流式读取 zip 内条目（调用方已预检存在性）。"""

    with zipfile.ZipFile(zip_path) as archive:
        info = _find_zip_entry(archive, name)
        if info is None:
            raise ValueError(f"压缩包内不存在条目：{name}")
        with archive.open(info) as source:
            while chunk := source.read(UPLOAD_CHUNK_BYTES):
                yield chunk


#: 进度文件的进程内互斥锁（按路径）：/predict 的 report_progress 与 /progress 读取共用。
#: Windows 上 read_text 与 temp.replace 并发会抛 PermissionError（WinError 5），必须同锁。
_PROGRESS_LOCKS: dict[str, threading.Lock] = {}
_PROGRESS_LOCKS_GUARD = threading.Lock()


def _progress_lock_for(path: Path) -> threading.Lock:
    key = str(path)
    with _PROGRESS_LOCKS_GUARD:
        lock = _PROGRESS_LOCKS.get(key)
        if lock is None:
            lock = _PROGRESS_LOCKS[key] = threading.Lock()
        return lock


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
                except ValueError as e:
                    raw_path.unlink(missing_ok=True)
                    return _fail(str(e))
                except (RuntimeError, OSError) as e:
                    raw_path.unlink(missing_ok=True)
                    log.warning("ZIP 解压失败: %s: %s", type(e).__name__, e)
                    return _fail("ZIP 解压失败，整批拒绝")
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
        progress_key = body.pop("progressKey", None)
        params: dict[str, Any] = body
        progress_data: dict[str, Any] = {}
        progress_lock = threading.Lock()

        def progress_file_path() -> Path | None:
            if not progress_key:
                return None
            safe_key = re.sub(r"[^A-Za-z0-9._-]", "_", str(progress_key))
            return OUTPUT_DIR / "_progress" / f"{safe_key}.json"

        def report_progress(**update: Any) -> None:
            path = progress_file_path()
            if path is None:
                return
            # 进度写失败只记日志，绝不允许穿透 core.run 把任务打挂
            try:
                with progress_lock, _progress_lock_for(path):
                    progress_data.update(update)
                    progress_data.update({
                        "key": str(progress_key),
                        "operator": OPERATOR_TAG,
                        "name": OPERATOR_NAME,
                        "updatedAt": datetime.now(timezone.utc).isoformat(),
                    })
                    path.parent.mkdir(parents=True, exist_ok=True)
                    temp = path.with_suffix(".tmp")
                    temp.write_text(json.dumps(progress_data, ensure_ascii=False), encoding="utf-8")
                    temp.replace(path)
            except Exception as e:
                log.warning("进度写入失败（不影响任务执行）: %s: %s", type(e).__name__, e)

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
            report_progress(status="running", startedAt=started.isoformat(),
                            total=0, processed=0, skipped=0, failed=0, review=0,
                            currentItem=None)
            # core.run 是长耗时同步调用，必须放进线程池：否则会占死事件循环，
            # 任务运行期间 /progress、/listFiles、/downloadFile 全部不可用。
            result = await run_in_threadpool(core.run, input_dir, output_dir, params,
                                             log=log.info, progress=report_progress)
            finished = datetime.now(timezone.utc)
            summary = result.get("summary", {})
            skipped_count = len(result.get("skipped", []))
            failed_count = len(result.get("failed", []))
            review_count = len(result.get("review", []))
            total_count = int(progress_data.get("total") or summary.get("total") or summary.get("pages") or 0)
            processed_value = progress_data.get("processed")
            processed_count = int(processed_value) if processed_value is not None else total_count
            succeeded_value = progress_data.get("succeeded")
            succeeded_count = (int(succeeded_value) if succeeded_value is not None
                               else max(0, total_count - skipped_count - failed_count))
            report_progress(status="completed", total=total_count, processed=processed_count,
                            succeeded=succeeded_count, skipped=skipped_count, failed=failed_count,
                            review=review_count, currentItem=None, finishedAt=finished.isoformat())

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

            progress_file = progress_file_path()
            return JSONResponse(_envelope(0, "success", {
                "outputFile": str(output_file),
                "lineageFile": str(lineage_file),
                "progressFile": str(progress_file) if progress_file else None,
                "summary": result.get("summary", {}),
                "skipped": result.get("skipped", []),
                "failed": result.get("failed", []),
            }))
        except ValueError as e:
            if progress_key:
                report_progress(status="failed", error=str(e), finishedAt=datetime.now(timezone.utc).isoformat())
            return _fail(str(e))
        except Exception as e:  # 核心异常包装为业务失败，不暴露堆栈
            if progress_key:
                report_progress(status="failed", error=f"{type(e).__name__}: {e}",
                                finishedAt=datetime.now(timezone.utc).isoformat())
            return _fail(f"算子执行失败：{type(e).__name__}: {e}")

    # ==================== 产物读取（平台 → 算子） ====================
    # 平台与算子不在同一服务器，产物只能经 HTTP 读取，契约见
    # platform-hsmty/docs/算子文件接口约定.md。path 统一是 /predict 返回的 data.outputFile，
    # 只允许 OUTPUT_DIR 之内、且不得是共享根本身（防跨任务枚举）。
    # 注意：本服务与 /uploadFile、/predict 一样无鉴权，部署时必须保证端口仅内网/平台网段可达。

    def _gate_output_path(path: str, label: str = "path") -> Path:
        target = _gate_path(path, label, roots=(OUTPUT_DIR,))
        if target == OUTPUT_DIR:
            raise ValueError(f"{label} 必须指向具体运行目录或产物文件")
        return target

    def _download_error(msg: str, status_code: int = 400) -> JSONResponse:
        # 下载失败必须返回非 200：平台把 200 的响应体直接当文件字节
        return JSONResponse({"code": 1, "msg": msg, "data": {}}, status_code=status_code)

    @app.get("/listFiles")
    def list_files(path: str = Query(...)) -> JSONResponse:
        try:
            target = _gate_output_path(path)
        except ValueError as e:
            return _fail(str(e))
        if not target.exists():
            return _ok([])
        try:
            if target.is_dir():
                # 递归列出全部文件（相对路径），与 zip 分支、平台本地模式（LocalOperatorFileService）一致；
                # 符号链接跳过，防止泄露闸外文件的存在性。
                entries: list[dict[str, Any]] = []
                for child in target.rglob("*"):
                    if child.is_symlink() or not child.is_file():
                        continue
                    entries.append({
                        "name": child.relative_to(target).as_posix(),
                        "size": child.stat().st_size,
                    })
                    if len(entries) > MAX_LIST_ENTRIES:
                        return _fail(f"产物文件数超过上限 {MAX_LIST_ENTRIES}")
                entries.sort(key=lambda e: e["name"])
                return _ok(entries)
            if target.suffix.lower() == ".zip":
                with zipfile.ZipFile(target) as archive:
                    infos = [info for info in archive.infolist() if not info.is_dir()]
                if len(infos) > MAX_LIST_ENTRIES:
                    return _fail(f"产物文件数超过上限 {MAX_LIST_ENTRIES}")
                return _ok([
                    {"name": _zip_entry_name(info), "size": info.file_size}
                    for info in infos
                ])
            return _ok([{"name": target.name, "size": target.stat().st_size}])
        except (OSError, zipfile.BadZipFile) as e:
            log.warning("listFiles 失败: path=%s %s: %s", path, type(e).__name__, e)
            return _fail(f"读取产物失败：{type(e).__name__}")

    @app.get("/downloadFile")
    def download_file(path: str = Query(...), name: str = Query(...)):
        try:
            target = _gate_output_path(path)
            entry = _safe_entry_name(name)
        except ValueError as e:
            return _download_error(str(e))
        if not target.exists():
            return _download_error("产物不存在", 404)
        try:
            if target.is_dir():
                child = _resolve_child(target, entry)
                if child.is_symlink() or not child.is_file():
                    return _download_error(f"文件不存在：{entry}", 404)
                # 先 stat 再交给 FileResponse（stat_result），避免发送期异常被全局
                # exception_handler 包装成 HTTP 200 的错误 JSON、被平台误存为文件内容
                st = child.stat()
                return FileResponse(child, media_type=_content_type(child.name), stat_result=st)
            if target.suffix.lower() == ".zip":
                with zipfile.ZipFile(target) as archive:
                    info = _find_zip_entry(archive, entry)
                if info is None:
                    return _download_error(f"压缩包内不存在条目：{entry}", 404)
                return StreamingResponse(
                    _iter_zip_entry(target, entry),
                    media_type=_content_type(entry),
                    headers={"Content-Length": str(info.file_size)},
                )
            if target.name != entry or not target.is_file():
                return _download_error(f"文件不存在：{entry}", 404)
            return FileResponse(target, media_type=_content_type(target.name),
                                stat_result=target.stat())
        except (OSError, ValueError, zipfile.BadZipFile) as e:
            log.warning("downloadFile 失败: path=%s name=%s %s: %s", path, name, type(e).__name__, e)
            return _download_error(f"读取产物失败：{type(e).__name__}")

    @app.get("/progress")
    def progress(runId: str = Query(...)) -> JSONResponse:
        # 与 /predict 的 report_progress 使用同一套键名规则与同一把进程内锁
        safe_key = re.sub(r"[^A-Za-z0-9._-]", "_", str(runId))
        path = OUTPUT_DIR / "_progress" / f"{safe_key}.json"
        if not path.is_file():
            return JSONResponse({"code": 1, "msg": "进度不存在", "data": {}})
        try:
            with _progress_lock_for(path):
                data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            return JSONResponse({"code": 1, "msg": f"进度读取失败：{type(e).__name__}", "data": {}})
        if not isinstance(data, dict):
            return JSONResponse({"code": 1, "msg": "进度格式非法", "data": {}})
        return _ok(data)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=DEFAULT_PORT)
