#!/usr/bin/env python3
"""
IDG音频检测调用示例：三期平台网关接口。

用法:
    python idg_audio_call.py <音频文件路径> [--detection 12a_wrong_value_orientation]
                            [--appkey-mode api_key|appid] [--mode-suffix predict1]
                            [--url http://10.252.92.98:9050/idg-audio-3qi]

环境变量(可选，有默认值):
    IDG_AUDIO_APPID            默认 idgaudio
    IDG_AUDIO_API_KEY          默认 07b9f895239cd84f906b19a727694b79
    IDG_AUDIO_CAPABILITY_NAME  默认 idg-audio-3qi

支持格式: .wav / .mp3 / .ogg / .flac（服务端校验扩展名）
"""
import argparse
import base64
import hashlib
import json
import os
import sys
import time
import uuid
from pathlib import Path

import requests

ALLOWED_EXTS = {".wav", ".mp3", ".ogg", ".flac"}


def make_headers(appid, api_key, capability_name, use_api_key_as_appkey=True):
    current_time = str(int(time.time()))
    csid = appid + capability_name + uuid.uuid4().hex
    server_param = base64.b64encode(
        json.dumps({"appid": appid, "csid": csid},
                   ensure_ascii=False).encode("utf-8")
    ).decode("utf-8")
    checksum = hashlib.md5(
        (api_key + current_time + server_param).encode("utf-8")
    ).hexdigest()
    return {
        "Authorization": "Bearer no-key",
        # ASR参考里 appKey 头放密钥；旧模板放 appid——两种模式都支持测试
        "appKey": api_key if use_api_key_as_appkey else appid,
        "X-CurTime": current_time,
        "X-Server-Param": server_param,
        "X-CheckSum": checksum,
    }


def main():
    parser = argparse.ArgumentParser(description="调用 IDG 音频检测接口")
    parser.add_argument("audio_file", type=Path, help="音频文件路径")
    parser.add_argument("--detection", default="12a_wrong_value_orientation",
                        help="算子 ID（12a~22a, 29a~34a, 43a~50a）")
    parser.add_argument("--url",
                        default="http://10.252.92.98:9050/idg-audio-3qi",
                        help="服务地址")
    parser.add_argument("--appkey-mode", choices=("api_key", "appid"),
                        default="api_key",
                        help="appKey 头放密钥(ASR参考方式)还是 appid(旧模板方式)")
    parser.add_argument("--mode-suffix", default=None,
                        help="URL 模式后缀，如 predict1")
    args = parser.parse_args()

    if not args.audio_file.is_file():
        raise SystemExit(f"音频文件不存在：{args.audio_file}")

    ext = args.audio_file.suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise SystemExit(f"不支持的音频格式 {ext}，仅支持: "
                         f"{', '.join(sorted(ALLOWED_EXTS))}")

    appid = os.environ.get("IDG_AUDIO_APPID", "idgaudio").strip()
    api_key = os.environ.get(
        "IDG_AUDIO_API_KEY", "07b9f895239cd84f906b19a727694b79").strip()
    capability = os.environ.get(
        "IDG_AUDIO_CAPABILITY_NAME", "idg-audio-3qi").strip()

    url = args.url.rstrip("/")
    if args.mode_suffix:
        url = url + "/" + args.mode_suffix.lstrip("/")
    url = url + "?detection=" + args.detection

    headers = make_headers(
        appid, api_key, capability,
        use_api_key_as_appkey=(args.appkey_mode == "api_key"))

    print(f"URL: {url}")
    print(f"Headers: {json.dumps(headers, ensure_ascii=False)}")
    print("-" * 60)

    with args.audio_file.open("rb") as f:
        response = requests.post(
            url,
            headers=headers,
            files={"file": (args.audio_file.name, f)},
            timeout=300,
        )

    print(f"HTTP 状态码: {response.status_code}")
    print(f"原始响应: {response.text[:2000]}")
    if response.text.strip():
        try:
            print(f"解析后 JSON:\n{json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        except Exception as exc:
            print(f"响应不是合法 JSON: {exc}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, requests.RequestException) as exc:
        print(f"调用失败：{exc}", file=sys.stderr)
        raise SystemExit(1)
