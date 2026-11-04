"""状态机与门禁回归用例（4.2）：逐条断言业务失败信息，全部符合预期才退出 0。"""

from __future__ import annotations

import time

import requests

BASE = "http://127.0.0.1:8090"
STAMP = time.strftime("%H%M%S")


def login() -> str:
    return requests.post(BASE + "/api/auth/login", timeout=30,
                         json={"username": "admin", "password": "admin123"}).json()["data"]["token"]


def call(token, method, path, **kw):
    r = requests.request(method, BASE + path, timeout=120,
                         headers={"Authorization": "Bearer " + token}, **kw)
    return r.json()


def expect_fail(token, method, path, keyword, **kw):
    body = call(token, method, path, **kw)
    ok = body.get("code") != 0 and keyword in (body.get("msg") or "")
    print(("PASS" if ok else "FAIL"), method, path, "→", body.get("msg"))
    return ok, body


def main() -> int:
    token = login()
    results = []

    # 1) 白名单外文件 → 校验后 upload_failed；上传失败批次不可编辑、可删除
    files = [("files", ("bad.txt", b"not allowed", "text/plain"))]
    batch = call(token, "POST", "/api/material/upload",
                 params={"line": "metadata", "name": f"REG-bad-{STAMP}"}, files=files)["data"]
    checked = call(token, "POST", f"/api/material/{batch['id']}/check")["data"]
    results.append((checked["status"] == "upload_failed", f"校验后状态={checked['status']}"))
    print(("PASS" if checked["status"] == "upload_failed" else "FAIL"), "upload_failed:", checked["status"])
    results.append(expect_fail(token, "PUT", f"/api/material/{batch['id']}",
                               "不可编辑", json={"name": "改名"}))
    deleted = call(token, "DELETE", f"/api/material/{batch['id']}")
    ok = deleted.get("code") == 0
    print(("PASS" if ok else "FAIL"), "上传失败批次可删除:", deleted.get("msg"))
    results.append((ok, "上传失败批次可删除"))

    # 2) 未校验/未移交批次不能建任务
    files = [("files", ("n.html", b"<html><body>test</body></html>", "text/html"))]
    pending = call(token, "POST", "/api/material/upload",
                   params={"line": "metadata", "name": f"REG-pending-{STAMP}"}, files=files)["data"]
    results.append(expect_fail(token, "POST", "/api/task", "未移交",
                               json={"name": "REG-未移交", "line": "metadata", "batchId": pending["id"]}))

    # 3) 已移交/已关联批次不可删除
    released = [b for b in call(token, "GET", "/api/material?line=metadata&pageSize=50")["data"]["records"]
                if b["status"] == "released" and b.get("linked")][0]
    results.append(expect_fail(token, "DELETE", f"/api/material/{released['id']}", "不可删除"))

    # 4) 图文任务必须选大类
    gbatch = [b for b in call(token, "GET", "/api/material?line=graphic&pageSize=50")["data"]["records"]
              if b["status"] == "released"][0]
    results.append(expect_fail(token, "POST", "/api/task", "大类",
                               json={"name": "REG-图文", "line": "graphic", "batchId": gbatch["id"]}))

    # 5) 草稿不能直接启动；只有待处理可启动
    draft = call(token, "POST", "/api/task", json={
        "name": f"REG-draft-{STAMP}", "line": "metadata", "batchId": released["id"]})["data"]
    results.append(expect_fail(token, "POST", f"/api/task/{draft['id']}/start", "仅待处理"))
    call(token, "POST", f"/api/task/{draft['id']}/submit")
    results.append(expect_fail(token, "POST", f"/api/task/{draft['id']}/submit", "仅草稿"))
    results.append(expect_fail(token, "DELETE", f"/api/task/{draft['id']}", "仅草稿"))

    # 6) 已出结论的阈值锁定
    meta_task = [t for t in call(token, "GET", "/api/task?line=metadata&pageSize=50")["data"]["records"]
                 if t["status"] == "collected"][0]
    results.append(expect_fail(token, "PUT", f"/api/task/{meta_task['id']}/threshold", "锁定",
                               json={"threshold": 0.9}))

    # 7) 归集仅待归集可做（已归集再归集应失败）
    results.append(expect_fail(token, "POST", f"/api/task/{meta_task['id']}/collect", "仅待归集"))

    # 8) 已闭环复核单不能再出结论 / 再闭环
    done_order = [o for o in call(token, "GET", "/api/review?status=done&pageSize=20")["data"]["records"]][0]
    results.append(expect_fail(token, "POST", f"/api/review/{done_order['id']}/close", "已闭环"))

    # 9) 非 published 数据集不能下载报告（metadata 已回滚）
    rolled = [d for d in call(token, "GET", "/api/dataset?line=metadata&pageSize=20")["data"]["records"]
              if d["status"] == "rolledback"][0]
    r = requests.get(BASE + f"/api/dataset/{rolled['id']}/report",
                     headers={"Authorization": "Bearer " + token}, timeout=30)
    ok = r.status_code == 200 and r.json().get("code") != 0
    print(("PASS" if ok else "FAIL"), "回滚数据集下载报告被拒:", r.text[:80])
    results.append((ok, "回滚后报告禁下"))

    bad = [r for r in results if not r[0]]
    print(f"\n共 {len(results)} 项，失败 {len(bad)} 项")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
