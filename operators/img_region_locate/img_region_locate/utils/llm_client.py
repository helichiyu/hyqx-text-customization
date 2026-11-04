"""大模型调用客户端（硅基流动，OpenAI 兼容）。

统一封装：重试、超时、JSON mode、JSON 提取、置信度截断、受限并发。
所有算子只通过本模块调模型，不直接 requests。
"""

from __future__ import annotations

import base64
import io
import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Iterable

import requests

try:  # 既可在 _shared_tools 顶层用，也可被 vendor 进算子内层包 utils/ 后用
    from . import llm_config as cfg
except ImportError:
    import llm_config as cfg

log = logging.getLogger("llm_client")

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class LlmError(Exception):
    """模型调用失败（重试耗尽或不可重试错误）。"""


class JsonParseError(LlmError):
    """模型返回内容不是可解析的 JSON。"""


def _post(payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {cfg.API_KEY}",
        "Content-Type": "application/json",
    }
    resp = requests.post(
        f"{cfg.BASE_URL}/chat/completions",
        headers=headers,
        json=payload,
        timeout=timeout,
    )
    if resp.status_code in _RETRYABLE_STATUS:
        raise LlmError(f"HTTP {resp.status_code}: {resp.text[:200]}")
    if resp.status_code != 200:
        # 4xx 不可重试（多为请求构造错误）
        raise LlmError(f"HTTP {resp.status_code}（不可重试）: {resp.text[:300]}")
    return resp.json()


def chat(
    messages: list[dict[str, Any]],
    *,
    model: str | None = None,
    json_mode: bool = True,
    max_tokens: int = 4096,
    temperature: float = cfg.TEMPERATURE,
    timeout: int = cfg.TIMEOUT_SECONDS,
    max_retries: int = cfg.MAX_RETRIES,
) -> str:
    """调用 chat/completions，返回 content 文本。失败重试 max_retries 次（最多 max_retries+1 次）。"""

    payload: dict[str, Any] = {
        "model": model or cfg.TEXT_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    last_err: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            data = _post(payload, timeout)
            content = data["choices"][0]["message"]["content"]
            if content is None or not str(content).strip():
                raise LlmError("模型返回空内容")
            return str(content)
        except (LlmError, requests.RequestException, KeyError, IndexError) as e:
            last_err = e
            if attempt < max_retries:
                wait = 2**attempt
                log.warning("模型调用失败（第 %d 次），%ds 后重试：%s", attempt + 1, wait, e)
                time.sleep(wait)
    raise LlmError(f"模型调用重试 {max_retries} 次仍失败：{last_err}")


def image_to_data_url(image: str | Path | Any, *, max_long_edge: int | None = None) -> str:
    """把 PIL Image 或图片路径转成 data URL；可选压缩长边（视觉调用前统一缩放）。"""

    from PIL import Image

    if isinstance(image, (str, Path)):
        img = Image.open(image)
        img.load()
    else:
        img = image
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    if max_long_edge:
        w, h = img.size
        long_edge = max(w, h)
        if long_edge > max_long_edge:
            scale = max_long_edge / long_edge
            img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def chat_vision(
    system_prompt: str,
    user_text: str,
    image: str | Path | Any,
    *,
    model: str | None = None,
    json_mode: bool = True,
    max_tokens: int = 4096,
    max_long_edge: int | None = None,
    **kwargs: Any,
) -> str:
    """视觉模型调用：system + (图片, 文本) 单轮。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": image_to_data_url(image, max_long_edge=max_long_edge)}},
                {"type": "text", "text": user_text},
            ],
        },
    ]
    return chat(messages, model=model or cfg.VISION_MODEL, json_mode=json_mode, max_tokens=max_tokens, **kwargs)


_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def extract_json(content: str) -> dict[str, Any]:
    """从模型输出中提取 JSON 对象：去 Markdown 围栏、截取首个 { 到末尾 }。失败抛 JsonParseError。"""

    text = _FENCE_RE.sub("", content.strip()).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise JsonParseError(f"输出中找不到 JSON 对象：{content[:120]!r}")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as e:
        raise JsonParseError(f"JSON 解析失败：{e}；片段：{text[start:start+120]!r}") from e


def clamp_confidence(value: Any) -> float | None:
    """置信度截断到 [0, 0.98]；无法解析返回 None。"""

    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return max(cfg.CONFIDENCE_MIN, min(cfg.CONFIDENCE_MAX, v))


def run_concurrent(
    items: Iterable[Any],
    fn: Callable[[Any], Any],
    *,
    concurrency: int | None = None,
    progress: Callable[..., None] | None = None,
) -> list[Any]:
    """受限并发执行 fn(item)，保持输入顺序返回结果，并报告样本级完成数。"""

    workers = max(1, min(cfg.MAX_CONCURRENCY, concurrency or cfg.DEFAULT_CONCURRENCY))
    items = list(items)
    total = len(items)
    if progress:
        progress(total=total, processed=0)
    if workers == 1 or total <= 1:
        results: list[Any] = []
        for index, item in enumerate(items, start=1):
            results.append(fn(item))
            if progress:
                progress(total=total, processed=index)
        return results
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fn, item): index for index, item in enumerate(items)}
        results = [None] * total
        completed = 0
        for future in as_completed(futures):
            index = futures[future]
            results[index] = future.result()
            completed += 1
            if progress:
                progress(total=total, processed=completed)
        return results
