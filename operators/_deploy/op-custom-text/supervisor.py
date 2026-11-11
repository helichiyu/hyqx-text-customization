"""op-custom-text 单容器进程管理：11 个算子独立进程 + nginx 路径路由。

设计取舍：
* 每个算子仍运行各自原有的 ``inference.py``，不修改算子实现，行为与单算子镜像一致；
* 每个算子独占一个进程，长任务不会阻塞其它算子或健康检查；
* 11 个算子全部 ``/healthz`` 通过后才启动 nginx，因此容器健康检查反映真实就绪状态；
* 任一算子或 nginx 退出即停止整个容器，交由 compose ``restart: unless-stopped`` 拉起，
  避免"半可用"状态下平台把任务派给已经挂掉的算子。
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
OPS_DIR = APP_DIR / "ops"
NGINX_CONF = str(APP_DIR / "nginx.conf")

# 算子目录名 -> 容器内回环端口（对外统一由 nginx 的 17022 按路径分流）。
TAGS = [
    ("meta_clean_slice", 7101),
    ("meta_genre_judge", 7102),
    ("meta_fact_extract", 7103),
    ("meta_field_fill", 7104),
    ("lay_page_render", 7105),
    ("lay_page_detect", 7106),
    ("fml_formula_locate", 7107),
    ("fml_formula_recognize", 7108),
    ("img_region_locate", 7109),
    ("img_type_classify", 7110),
    ("img_struct_describe", 7111),
]

READY_TIMEOUT_SECONDS = int(os.getenv("READY_TIMEOUT_SECONDS", "300"))
SHUTDOWN_GRACE_SECONDS = 20

log = logging.getLogger("supervisor")
children: list[subprocess.Popen] = []
stop_requested = threading.Event()


def _health(port: int) -> bool:
    """单算子就绪探测。"""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def _spawn_operator(tag: str, port: int) -> subprocess.Popen:
    env = os.environ.copy()
    env["PORT"] = str(port)
    log.info("starting operator %s on 127.0.0.1:%d", tag, port)
    proc = subprocess.Popen([sys.executable, "inference.py"], cwd=str(OPS_DIR / tag), env=env)
    children.append(proc)
    return proc


def _wait_ready(procs: dict[str, subprocess.Popen]) -> bool:
    pending = {tag: port for tag, port in TAGS}
    deadline = time.monotonic() + READY_TIMEOUT_SECONDS
    last_report = 0.0

    while pending and time.monotonic() < deadline:
        if stop_requested.is_set():
            return False
        for tag, port in list(pending.items()):
            proc = procs[tag]
            if proc.poll() is not None:
                log.error("operator %s exited before ready (code=%s)", tag, proc.returncode)
                return False
            if _health(port):
                log.info("operator %s ready", tag)
                pending.pop(tag)

        now = time.monotonic()
        if pending and now - last_report >= 15:
            log.info("waiting for %d operator(s): %s", len(pending), ", ".join(pending))
            last_report = now
        if pending:
            time.sleep(1)

    if pending:
        log.error("operators not ready within %ss: %s", READY_TIMEOUT_SECONDS, ", ".join(pending))
        return False
    return True


def _terminate_all() -> None:
    for proc in children:
        if proc.poll() is None:
            try:
                proc.terminate()
            except ProcessLookupError:
                pass

    deadline = time.monotonic() + SHUTDOWN_GRACE_SECONDS
    for proc in children:
        remaining = max(0.0, deadline - time.monotonic())
        try:
            proc.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass


def _handle_signal(signum: int, _frame: object) -> None:
    log.info("received signal %s, shutting down", signum)
    stop_requested.set()


def main() -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s supervisor %(message)s")
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    procs = {tag: _spawn_operator(tag, port) for tag, port in TAGS}
    if not _wait_ready(procs):
        _terminate_all()
        return 1
    if stop_requested.is_set():
        _terminate_all()
        return 0

    log.info("all 11 operators ready, starting nginx on :17022")
    nginx = subprocess.Popen(["nginx", "-c", NGINX_CONF, "-g", "daemon off;"])
    children.append(nginx)

    while not stop_requested.is_set():
        for tag, proc in procs.items():
            code = proc.poll()
            if code is not None:
                log.error("operator %s exited (code=%s); stopping container", tag, code)
                _terminate_all()
                return 1
        code = nginx.poll()
        if code is not None:
            log.error("nginx exited (code=%s); stopping container", code)
            _terminate_all()
            return 1
        stop_requested.wait(2)

    _terminate_all()
    return 0


if __name__ == "__main__":
    sys.exit(main())
