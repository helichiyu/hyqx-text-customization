"""四产线端到端驱动：上传 → 校验 → 移交 → 建任务 → 提交 → 启动 → 轮询到阶段结束。

用法（项目根）：
    .venv/Scripts/python.exe -I platform/scripts/e2e_lines.py [line ...]

依赖：requests（见 operators/_shared_tools 运行环境记录）。
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8090"
POOL = Path(__file__).resolve().parents[2] / "samples_pool"

FILES = {
    "metadata": ["meta/news_001.html", "meta/news_002.html", "meta/nonnews_navlist.html",
                 "meta/nonnews_product.html", "meta/nonnews_tutorial.html"],
    "layout": ["lay/layout_sample.pdf", "lay/encrypted.pdf"],
    "formula": ["fml/formula_sample.pdf"],
    "graphic": ["img/geometry_001.jpg", "img/chart_001.jpg", "img/table_001.jpg",
                "img/schematic_001.jpg", "img/lowres_001.jpg"],
}
IMAGE_CLASS = {"graphic": "统计"}
STAMP = time.strftime("%H%M%S")


def call(method: str, path: str, token: str | None = None, **kw):
    headers = kw.pop("headers", {})
    if token:
        headers["Authorization"] = "Bearer " + token
    r = requests.request(method, BASE + path, headers=headers, timeout=1800, **kw)
    try:
        body = r.json()
    except Exception:
        raise RuntimeError(f"{method} {path} 非 JSON 响应: {r.status_code} {r.text[:300]}")
    if body.get("code") != 0:
        raise RuntimeError(f"{method} {path} 业务失败: {body.get('msg')}")
    return body.get("data")


def run_line(line: str, token: str) -> dict:
    t0 = time.time()
    files = [("files", (Path(f).name, (POOL / f).read_bytes(), "application/octet-stream"))
             for f in FILES[line]]
    batch = call("POST", "/api/material/upload", token,
                 params={"line": line, "name": f"E2E-{line}-{STAMP}"}, files=files)
    batch_id = batch["id"]
    checked = call("POST", f"/api/material/{batch_id}/check", token)
    released = call("POST", f"/api/material/{batch_id}/release", token)
    task = call("POST", "/api/task", token, json={
        "name": f"E2E-{line}-{STAMP}",
        "line": line,
        "batchId": batch_id,
        "priority": "mid",
        "imageClass": IMAGE_CLASS.get(line),
        "threshold": 0.8,
    })
    task_id = task["id"]
    call("POST", f"/api/task/{task_id}/submit", token)
    call("POST", f"/api/task/{task_id}/start", token)

    deadline = time.time() + 1800
    last = None
    while time.time() < deadline:
        detail = call("GET", f"/api/task/{task_id}", token)
        status = detail.get("status") or (detail.get("task") or {}).get("status")
        if status != last:
            print(f"  [{line}] task={task_id} status={status}", flush=True)
            last = status
        if status in ("waitreview", "quality", "collected", "failed"):
            break
        time.sleep(5)
    else:
        status = "timeout"

    runs = detail.get("stageRuns") or []
    ds = call("GET", "/api/dataset", token, params={"line": line, "pageSize": 50})
    mine = [d for d in ds.get("records", ds.get("rows", [])) if d.get("taskId") == task_id]
    reviews = call("GET", "/api/review", token, params={"taskId": task_id})
    return {
        "line": line,
        "batchId": batch_id,
        "batchStatus": released.get("status"),
        "taskId": task_id,
        "status": status,
        "elapsed": round(time.time() - t0, 1),
        "runs": [{k: r.get(k) for k in ("stageNo", "operatorTag", "status", "summary", "errorMsg")}
                 for r in runs],
        "datasets": [{k: d.get(k) for k in ("id", "bizNo", "status", "itemCount", "semVer")} for d in mine],
        "reviewOrders": len(reviews.get("records", reviews.get("rows", []))),
    }


def main() -> int:
    token = call("POST", "/api/auth/login", json={"username": "admin", "password": "admin123"})["token"]
    lines = sys.argv[1:] or ["metadata", "layout", "formula", "graphic"]
    results = []
    for line in lines:
        print(f"== {line} ==", flush=True)
        try:
            results.append(run_line(line, token))
        except Exception as e:  # 单线失败不阻断其它线
            results.append({"line": line, "error": str(e)})
            print(f"  [{line}] ERROR {e}", flush=True)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if all("error" not in r and r.get("status") not in ("timeout", "failed") for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
