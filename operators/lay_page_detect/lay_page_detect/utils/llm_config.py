"""大模型调用配置（硅基流动，OpenAI 兼容）。

API key 按用户指示直接写入代码；环境变量 SILICONFLOW_API_KEY / SILICONFLOW_BASE_URL
可覆盖，便于交付环境替换。
"""

from __future__ import annotations

import os

BASE_URL = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
API_KEY = os.getenv(
    "SILICONFLOW_API_KEY",
    "sk-sntgzyndiukafftszxatgcjfawdneobqkhravkgysxounyoh",
)

#: 视觉模型默认值（版面检测 / 公式定位与识别 / 图片判型与描述）。
#: 冒烟验证：grounding（bbox 0-1000 归一化）与 LaTeX 识别在 32B 与 8B 上均可用；
#: 8B 于 2026-11-09 完成单点冒烟 + lay/fml/img 三链真实数据复验后设为默认。
VISION_MODEL = os.getenv("VISION_MODEL", "Qwen/Qwen3-VL-8B-Instruct")

#: 文本模型默认值（体裁判定 / 事实抽取 / 元信息补全）。
#: 冒烟验证：DeepSeek-V3.2 的 response_format=json_object 可用。
TEXT_MODEL = os.getenv("TEXT_MODEL", "deepseek-ai/DeepSeek-V3.2")

#: 统一调用约定（四份交付说明一致口径）
TEMPERATURE = 0.0
TIMEOUT_SECONDS = 60
MAX_RETRIES = 2  # 重试 2 次，即最多调用 3 次
DEFAULT_CONCURRENCY = 4  # 算子内并发，可配范围 4-8
MAX_CONCURRENCY = 8

#: 置信度合法区间（模型禁止输出 1.0，越界截断）
CONFIDENCE_MIN = 0.0
CONFIDENCE_MAX = 0.98
