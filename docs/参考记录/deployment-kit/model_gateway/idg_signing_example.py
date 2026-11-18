"""IDG/磐智 model gateway signing example. No credentials are embedded."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import uuid

import httpx


def make_headers(app_id: str, app_key: str, capability: str) -> dict[str, str]:
    if not app_id or not app_key or not capability:
        raise ValueError("APPID, APPKEY and capability are required")
    if len(capability) > 24:
        raise ValueError("capability must be at most 24 characters")
    timestamp = str(int(time.time()))
    csid = f"{app_id}{capability.ljust(24, '0')}{uuid.uuid4().hex}"
    server_param = base64.b64encode(
        json.dumps({"appid": app_id, "csid": csid}, ensure_ascii=False).encode("utf-8")
    ).decode("ascii")
    checksum = hashlib.md5((app_key + timestamp + server_param).encode("utf-8")).hexdigest()
    return {
        "Content-Type": "application/json",
        "appKey": app_key,
        "X-Server-Param": server_param,
        "X-CurTime": timestamp,
        "X-CheckSum": checksum,
    }


def chat(base_url: str, path: str, model: str, prompt: str) -> str:
    app_id = os.environ["MODEL_APP_ID"]
    app_key = os.environ["MODEL_APP_KEY"]
    capability = path.strip("/").split("/", 1)[0]
    url = base_url.rstrip("/") + "/" + path.lstrip("/")
    response = httpx.post(
        url,
        headers=make_headers(app_id, app_key, capability),
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        },
        timeout=300,
    )
    response.raise_for_status()
    if response.headers.get("X-Code") not in (None, "1000000"):
        raise RuntimeError(f"Gateway X-Code={response.headers.get('X-Code')}")
    if response.headers.get("X-IsSync", "").lower() == "false":
        raise RuntimeError("Gateway returned asynchronous response")
    body = response.json()
    return body["choices"][0]["message"]["content"]


if __name__ == "__main__":
    print(chat(
        os.environ["MODEL_GATEWAY_BASE_URL"],
        os.environ.get("MODEL_PATH", "/data-qwen35-2b-api"),
        os.environ.get("MODEL_NAME", "Qwen3.5-2B"),
        "只回复 OK",
    ))
