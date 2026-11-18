"""大模型调用客户端：默认 IDG/磐智模型网关，SiliconFlow 为回退后端。

统一封装：重试、超时、JSON mode、JSON 提取、置信度截断、受限并发。
所有算子只通过本模块调模型，不直接 requests。

IDG/磐智网关（升级要求第二节）：
- URL = MODEL_GATEWAY_BASE_URL + 模型 PATH（PATH 逐字取模型清单值，区分模型）；
- 签名头：appKey / X-Server-Param / X-CurTime / X-CheckSum，
  capability = PATH 首段右补 "0" 到 24 位，csid = APPID + capability + uuid，
  X-Server-Param = base64(json({"appid","csid"}))，
  X-CheckSum = md5(APPKEY + X-CurTime + X-Server-Param)；
- Qwen3 系文本模型请求体带 enable_thinking=false，避免思考过程污染正文；
- 校验响应头：X-Code 为空或 1000000；X-IsSync 不能为 false；
- 凭据只从环境变量读取，不出现在日志与错误消息中。
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import logging
import re
import time
import uuid
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


class LlmConfigError(LlmError):
    """调用配置错误（缺凭据/缺 PATH），重试无意义，直接抛出。"""


class JsonParseError(LlmError):
    """模型返回内容不是可解析的 JSON。"""


# ==================== IDG/磐智网关签名 ====================

def _idg_headers(model_path: str) -> dict[str, str]:
    """按升级要求 2.2 生成网关签名头；APPKEY 缺失时直接报错（不含敏感值）。"""

    if not cfg.MODEL_APP_KEY:
        raise LlmConfigError("MODEL_PROVIDER=idg 但未设置 MODEL_APP_KEY 环境变量")
    capability = model_path.lstrip("/").split("/", 1)[0]
    if not 1 <= len(capability) <= 24:
        raise LlmConfigError(f"模型 PATH 首段长度应为 1 至 24 个字符：{model_path!r}")
    csid = cfg.MODEL_APP_ID + capability.ljust(24, "0") + uuid.uuid4().hex
    server_param = base64.b64encode(
        json.dumps({"appid": cfg.MODEL_APP_ID, "csid": csid}).encode("utf-8")).decode("ascii")
    cur_time = str(int(time.time()))
    check_sum = hashlib.md5((cfg.MODEL_APP_KEY + cur_time + server_param).encode("utf-8")).hexdigest()
    return {
        "Content-Type": "application/json",
        "appKey": cfg.MODEL_APP_KEY,
        "X-Server-Param": server_param,
        "X-CurTime": cur_time,
        "X-CheckSum": check_sum,
    }


def _post(payload: dict[str, Any], timeout: int, *, path: str | None = None) -> dict[str, Any]:
    """单次调用。idg：POST 到 <网关>/<模型PATH> 并校验 X-Code/X-IsSync；
    siliconflow：POST 到 <base>/chat/completions（Bearer）。"""

    if cfg.is_idg():
        if not path:
            raise LlmConfigError("IDG 网关调用缺少模型 PATH")
        resp = requests.post(
            f"{cfg.MODEL_GATEWAY_BASE_URL}{path}",
            headers=_idg_headers(path),
            json=payload,
            timeout=timeout,
        )
        x_code = resp.headers.get("X-Code")
        if resp.status_code in _RETRYABLE_STATUS:
            raise LlmError(f"HTTP {resp.status_code}: {resp.text[:200]}")
        if resp.status_code != 200 or x_code not in (None, "1000000"):
            raise LlmError(f"网关拒绝：HTTP {resp.status_code}，X-Code={x_code}（不可重试）")
        if resp.headers.get("X-IsSync", "").strip().lower() == "false":
            raise LlmError("网关返回异步任务（X-IsSync=false），chat 接口不支持")
        return resp.json()

    if not cfg.SILICONFLOW_API_KEY:
        raise LlmConfigError("MODEL_PROVIDER=siliconflow 但未设置 SILICONFLOW_API_KEY 环境变量")
    resp = requests.post(
        f"{cfg.SILICONFLOW_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {cfg.SILICONFLOW_API_KEY}",
                 "Content-Type": "application/json"},
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
    timeout: int | None = None,
    max_retries: int | None = None,
    _vision: bool = False,
) -> str:
    """调用文本/视觉 chat 接口，返回 content 文本。失败重试 max_retries 次（最多 max_retries+1 次）。"""

    if cfg.is_idg():
        resolved_model = model or (cfg.VISION_MODEL if _vision else cfg.TEXT_MODEL)
        path = cfg.VISION_MODEL_PATH if _vision else cfg.TEXT_MODEL_PATH
    else:
        resolved_model = model or (cfg.SILICONFLOW_VISION_MODEL if _vision else cfg.SILICONFLOW_TEXT_MODEL)
        path = None
    timeout = cfg.default_timeout() if timeout is None else timeout
    max_retries = cfg.default_retries() if max_retries is None else max_retries

    payload: dict[str, Any] = {
        "model": resolved_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    if cfg.is_idg() and not _vision:
        # 升级要求 2.5：Qwen3 系文本模型关闭思考过程，避免污染正文
        payload["enable_thinking"] = False

    last_err: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            data = _post(payload, timeout, path=path)
            content = data["choices"][0]["message"]["content"]
            if content is None or not str(content).strip():
                raise LlmError("模型返回空内容")
            return str(content)
        except LlmConfigError:
            raise
        except (LlmError, requests.RequestException, KeyError, IndexError) as e:
            last_err = e
            if "不可重试" in str(e):  # 4xx / 网关拒绝：重试无意义
                break
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
    return chat(messages, model=model, json_mode=json_mode, max_tokens=max_tokens, _vision=True, **kwargs)


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
