"""四产线收尾：复核结论 → 整单闭环 → 归集 → 数据集发布 → 质量报告下载（可选回滚）。

用法（项目根）：
    .venv/Scripts/python.exe -I platform/scripts/e2e_finish.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8090"
OUT = Path(__file__).resolve().parents[2] / "platform" / "scripts" / "e2e_out"


def call(method: str, path: str, token: str, **kw):
    headers = {"Authorization": "Bearer " + token}
    r = requests.request(method, BASE + path, headers=headers, timeout=120, **kw)
    if r.headers.get("content-type", "").startswith("application/json"):
        body = r.json()
        if body.get("code") != 0:
            raise RuntimeError(f"{method} {path} 失败: {body.get('msg')}")
        return body.get("data")
    return r.content


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    login = requests.post(BASE + "/api/auth/login", timeout=30,
                          json={"username": "admin", "password": "admin123"}).json()
    token = login["data"]["token"]

    tasks = call("GET", "/api/task?pageSize=50", token)["records"]
    results = []
    for task in sorted(tasks, key=lambda t: t["line"]):
        if task["status"] != "waitreview":
            continue
        line = task["line"]
        orders = call("GET", f"/api/review?taskId={task['id']}&pageSize=20", token)["records"]
        item_actions = []
        for order in orders:
            detail = call("GET", f"/api/review/{order['id']}", token)
            for item in detail.get("items", []):
                action = "A"
                payload = None
                # 覆盖 B（修正）与 C（剔除）路径各一次
                if line == "metadata" and item_actions.count("B") == 0 and item["itemKey"] == "news_001":
                    action, payload = "B", {"reviewStatus": "已复核"}
                elif line == "layout":
                    action = "C"
                call("POST", f"/api/review/item/{item['id']}/conclude", token,
                     json={"conclusion": action, "revisedPayload": payload})
                item_actions.append(action)
            call("POST", f"/api/review/{order['id']}/close", token)

        detail = call("GET", f"/api/task/{task['id']}", token)
        if detail["status"] != "quality":
            raise RuntimeError(f"闭环后任务状态异常: {line} {detail['status']}")
        call("POST", f"/api/task/{task['id']}/collect", token)

        ds = [d for d in call("GET", f"/api/dataset?line={line}&pageSize=20", token)["records"]
              if d.get("taskId") == task["id"]][0]
        published = call("POST", f"/api/dataset/{ds['id']}/publish", token)
        report = call("GET", f"/api/dataset/{ds['id']}/report", token)
        report_file = OUT / f"report_{line}.txt"
        report_file.write_bytes(report)

        rolled = None
        if line == "metadata":
            rolled = call("POST", f"/api/dataset/{ds['id']}/rollback", token,
                          json={"reason": "E2E 回滚验证：发布后回退"})

        results.append({
            "line": line,
            "task": task["bizNo"],
            "orders": len(orders),
            "actions": item_actions,
            "dataset": ds["bizNo"],
            "publishedStatus": published["status"],
            "reportBytes": len(report),
            "reportHead": report.decode("utf-8", "replace").splitlines()[:6],
            "rollbackStatus": rolled["status"] if rolled else None,
        })
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
