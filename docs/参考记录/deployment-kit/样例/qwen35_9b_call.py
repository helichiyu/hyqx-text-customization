"""供给平台通过磐智 HTTP 网关调用 Qwen3.5-9B 的文本联调脚本。

依赖 requests。用 --gateway 或 PANZHI_GATEWAY 指定网关基址（协议、IP、端口）。
APPKEY 由 PANZHI_APPKEY 注入，交互运行时也可以按提示输入。
"""

import argparse
import base64
import getpass
import hashlib
import json
import os
import sys
import time
import uuid
from urllib.parse import urlsplit

import requests


APPID = "audioasr"
ROUTE = "/Qwen3.5-9B"
DEFAULT_MODEL = "Qwen3.5-9B"


def make_headers(appkey, capability):
    if not appkey or not appkey.strip():
        raise ValueError("请提供磐智应用的 APPKEY")
    if len(capability) > 24 or not capability:
        raise ValueError("能力名长度应为 1 至 24 个字符")
    # 配套 header.txt 用 PATH 首段并右补 0。PDF 要求字母数字；
    # 此路由含标点，如平台另有登记的签名能力名，请用 --capability 指定。
    if capability != ROUTE[1:] and not (capability.isascii() and capability.isalnum()):
        raise ValueError("自定义签名能力名应为 ASCII 字母或数字")
    csid = APPID + capability.ljust(24, "0") + uuid.uuid4().hex
    param = json.dumps({"appid": APPID, "csid": csid}).encode("utf-8")
    encoded = base64.b64encode(param).decode("ascii")
    timestamp = str(int(time.time()))
    checksum = hashlib.md5((appkey + timestamp + encoded).encode("utf-8")).hexdigest()
    return {
        "Content-Type": "application/json",
        "appKey": appkey,
        "X-Server-Param": encoded,
        "X-CurTime": timestamp,
        "X-CheckSum": checksum,
    }


def call_qwen(prompt, *, gateway, appkey, model=DEFAULT_MODEL, capability=ROUTE[1:]):
    """向网关发送一条非流式对话请求，返回解析后的业务 JSON。"""
    parts = urlsplit(gateway.strip())
    if (parts.scheme not in ("http", "https") or not parts.hostname
            or parts.username is not None or parts.password is not None
            or parts.path not in ("", "/") or parts.query or parts.fragment):
        raise ValueError("网关基址应形如 http://网关IP:端口，脚本会自动添加 /Qwen3.5-9B")
    if not prompt.strip() or not model.strip():
        raise ValueError("提示词和模型标识不能为空")
    url = parts.scheme + "://" + parts.netloc + ROUTE
    headers = make_headers(appkey, capability)
    # 只在部署方要求后端 Authorization 时配置完整头值。
    if os.environ.get("PANZHI_AUTHORIZATION"):
        headers["Authorization"] = os.environ["PANZHI_AUTHORIZATION"]
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    try:
        with requests.post(url, headers=headers, json=payload, timeout=(10, 300),
                           allow_redirects=False) as response:
            code = response.headers.get("X-Code")
            if not 200 <= response.status_code < 300 or code not in (None, "1000000"):
                raise RuntimeError(f"调用失败，HTTP {response.status_code}，X-Code={code}")
            if response.headers.get("X-IsSync", "").strip().lower() == "false":
                raise RuntimeError("网关返回异步确认，本脚本期望同步对话响应")
            try:
                return response.json()
            except ValueError:
                raise RuntimeError("响应不是 JSON，请核对服务 PATH 和响应类型") from None
    except requests.Timeout:
        raise RuntimeError("网关连接或模型响应超时") from None
    except requests.RequestException:
        raise RuntimeError("HTTP 请求失败，请核对网关地址、端口和网络配置") from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt", help="发给模型的文本")
    parser.add_argument("--gateway", default=os.getenv("PANZHI_GATEWAY"),
                        help="供给平台可达的网关基址，例如 http://网关IP:9050")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="部署服务接受的模型标识")
    parser.add_argument("--capability", default=ROUTE[1:], help="签名使用的能力名称")
    parser.add_argument("--raw", action="store_true", help="输出模型返回的完整 JSON")
    args = parser.parse_args()
    if not args.gateway:
        parser.error("请通过 --gateway 或 PANZHI_GATEWAY 指定真实网关基址")
    appkey = os.environ.get("PANZHI_APPKEY", "").strip()
    if not appkey:
        if not sys.stdin.isatty():
            parser.error("非交互运行时需要设置 PANZHI_APPKEY")
        appkey = getpass.getpass("请输入磐智 APPKEY（不回显）: ").strip()

    result = call_qwen(args.prompt, gateway=args.gateway, appkey=appkey,
                       model=args.model, capability=args.capability)
    if args.raw:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    if isinstance(result, dict) and result.get("error"):
        if not args.raw:
            print(json.dumps(result["error"], ensure_ascii=False), file=sys.stderr)
        raise RuntimeError("模型服务返回业务错误")
    if not args.raw:
        try:
            answer = result["choices"][0]["message"]["content"]
        except (TypeError, KeyError, IndexError):
            answer = None
        if not isinstance(answer, str):
            print(json.dumps(result, ensure_ascii=False, indent=2), file=sys.stderr)
            raise RuntimeError("未找到文本字段 choices[0].message.content，上方为实际返回")
        print(answer)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, EOFError) as exc:
        sys.exit(str(exc))
