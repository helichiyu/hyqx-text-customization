"""统一大模型网关（硅基流动 API，临时方案）。

2026-11-01 拍板：所有用到大模型的算子统一走本网关（base/key 硬编码为
临时方案，支持环境变量覆盖；后续切内部 vLLM 时只改此处）。
- 聊天/判别模型：THUDM/GLM-4-32B-0414（OpenAI 兼容 /chat/completions）
- 向量模型（#22/#31 embedding 升级位预留）：/embeddings，默认 BAAI/bge-m3

依赖：仅标准库 urllib（不引入 requests）。
超时 60s、失败重试 1 次；JSON 解析容忍代码围栏与前后缀文本。
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.request
from typing import List, Optional

# ==== 硬编码凭据（用户指定直接写入；环境变量可覆盖，换钥/换端点零改码）====
API_KEY = "sk-sntgzyndiukafftszxatgcjfawdneobqkhravkgysxounyoh"
BASE_URL = "https://api.siliconflow.cn/v1"
CHAT_MODEL = "THUDM/GLM-4-32B-0414"
EMBED_MODEL = "BAAI/bge-m3"
# 视觉模型（#5/#8 OCR）：与自部署版同款（华为平台无法部署 PaddleOCR-VL，2026-11 换型）
VISION_MODEL = "Qwen/Qwen3-VL-8B-Instruct"

TIMEOUT_SECONDS = 60
VISION_TIMEOUT_SECONDS = 120   # 视觉模型推理较慢
RETRIES = 1


class LlmApiError(RuntimeError):
    """API 调用失败（网络/鉴权/限流/超时）——调用方可据此降级。"""


def _conf() -> dict:
    return {
        "key": os.getenv("SILICONFLOW_API_KEY", API_KEY),
        "base": os.getenv("SILICONFLOW_BASE_URL", BASE_URL).rstrip("/"),
        "chat_model": os.getenv("LLM_MODEL", CHAT_MODEL),
        "embed_model": os.getenv("LLM_EMBED_MODEL", EMBED_MODEL),
        "vision_model": os.getenv("LLM_VISION_MODEL", VISION_MODEL),
    }


def chat_vision(images_b64: List[str], prompt: str, max_tokens: int = 2000,
                timeout: int = VISION_TIMEOUT_SECONDS, mime: str = "image/png") -> str:
    """多模态调用（OpenAI 兼容 image_url 格式）→ content。

    images_b64: base64 编码的图片列表（不带头部）。硅基流动同款模型与
    内部自部署 Qwen3-VL-8B-Instruct 行为一致，切换只改 BASE_URL/模型名。
    """
    conf = _conf()
    content = [{"type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{b64}"}}
               for b64 in images_b64]
    content.append({"type": "text", "text": prompt})
    body = json.dumps({
        "model": conf["vision_model"],
        "messages": [{"role": "user", "content": content}],
        "temperature": 0,
        "max_tokens": max_tokens,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{conf['base']}/chat/completions", data=body,
        headers={"Authorization": f"Bearer {conf['key']}",
                 "Content-Type": "application/json"})
    last_error: Optional[Exception] = None
    for attempt in range(RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"] or ""
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < RETRIES:
                time.sleep(1.5)
    raise LlmApiError(f"视觉模型调用失败: {last_error}")


def chat(messages: List[dict], temperature: float = 0.0, max_tokens: int = 500,
         timeout: int = TIMEOUT_SECONDS) -> str:
    """OpenAI 兼容 chat completions → content 字符串。"""
    conf = _conf()
    body = json.dumps({
        "model": conf["chat_model"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{conf['base']}/chat/completions", data=body,
        headers={"Authorization": f"Bearer {conf['key']}",
                 "Content-Type": "application/json"})
    last_error: Optional[Exception] = None
    for attempt in range(RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"] or ""
        except Exception as exc:  # noqa: BLE001 - 网络层错误统一降级口径
            last_error = exc
            if attempt < RETRIES:
                time.sleep(1.5)
    raise LlmApiError(f"LLM 调用失败: {last_error}")


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```")


def extract_json(content: str):
    """从模型返回中提取 JSON（容忍 ```json 围栏与前后缀说明文字）。"""
    text = content.strip()
    fenced = _JSON_FENCE_RE.search(text)
    if fenced:
        text = fenced.group(1).strip()
    # 找第一个对象/数组起点截到最后一个终点
    for opener, closer in (("[", "]"), ("{", "}")):
        start = text.find(opener)
        if start != -1:
            end = text.rfind(closer)
            if end > start:
                return json.loads(text[start:end + 1])
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise LlmApiError(f"模型返回非 JSON: {content[:120]}") from exc


def chat_json(messages: List[dict], **kwargs):
    """chat + JSON 提取一步到位。"""
    return extract_json(chat(messages, **kwargs))


def embeddings(texts: List[str], timeout: int = TIMEOUT_SECONDS) -> List[List[float]]:
    """/embeddings（#22/#31 语义升级位用；与聊天同 base/key）。"""
    conf = _conf()
    body = json.dumps({"model": conf["embed_model"], "input": texts}).encode("utf-8")
    req = urllib.request.Request(
        f"{conf['base']}/embeddings", data=body,
        headers={"Authorization": f"Bearer {conf['key']}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
        return [item["embedding"] for item in data["data"]]
    except Exception as exc:  # noqa: BLE001
        raise LlmApiError(f"embedding 调用失败: {exc}") from exc


# ==== 高层能力：错别字检测（#15/#32 共用，与各算子的规则引擎同签名）====

TYPO_SYSTEM = "你是中文文本错别字检测器，只找出真正写错的字词，不把正确词汇、专有名词、网络用语当错字。只返回纯JSON。"
TYPO_USER_TMPL = ("检查以下文本中的错别字，以JSON数组返回，每个元素为 {{\"word\": \"错误的词\"}}"
                  "（word 必须是原文中连续出现的片段）。没有错别字返回 []。不要输出任何其他内容。\n\n文本：{text}")
TYPO_TEXT_LIMIT = 4000   # 送检长度上限（超长截断；错误率分母仍按全文）


class TypoDetectorLlm:
    """GLM 零样本错别字检测。detect(text) -> (errorRate, hits[{word,position}])。"""

    name = "glm-4-32b-typo"

    def detect(self, text: str):
        stripped = text.strip()
        if not stripped:
            return 0.0, []
        result = chat_json(
            [{"role": "system", "content": TYPO_SYSTEM},
             {"role": "user", "content": TYPO_USER_TMPL.format(text=stripped[:TYPO_TEXT_LIMIT])}],
            max_tokens=500)
        words = [str(item.get("word", "")).strip()
                 for item in (result if isinstance(result, list) else [])
                 if isinstance(item, dict) and item.get("word")]
        # 模型返回的词定位到原文（找不到的丢弃——防幻觉词）
        hits, seen_spans = [], []
        for word in words:
            if not word:
                continue
            start = stripped.find(word)
            while start != -1:
                span = (start, start + len(word))
                if not any(s <= start < e for s, e in seen_spans):
                    seen_spans.append(span)
                    hits.append({"word": word,
                                 "position": {"start": start, "end": span[1]}})
                    break
                start = stripped.find(word, start + 1)
        hits.sort(key=lambda h: h["position"]["start"])
        wrong_chars = sum(h["position"]["end"] - h["position"]["start"] for h in hits)
        return round(wrong_chars / max(1, len(stripped)), 4), hits
