"""大模型调用配置：默认走 IDG/磐智模型网关，SiliconFlow 保留为回退后端。

升级要求第四节（环境变量分层）：可变配置一律环境变量注入，不写死代码；
凭据（MODEL_APP_KEY / SILICONFLOW_API_KEY）不落代码、Git、日志，
本地联调放入未入库的 operators/.env，生产由 K8s Secret 注入。

切换后端只改环境变量，无需改代码、无需重建镜像：
- 默认/切回磐智：MODEL_PROVIDER=idg（网关地址、APPID、模型、PATH 均有默认值）
- 切回退后端：MODEL_PROVIDER=siliconflow + SILICONFLOW_API_KEY
"""

from __future__ import annotations

import os

#: 模型后端开关：idg（IDG/磐智模型网关，默认）/ siliconflow（第三方回退）
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "idg").strip().lower()

# ==================== IDG/磐智模型网关 ====================

#: 网关基址（模型由 PATH 区分，PATH 必须逐字使用模型清单的值）
MODEL_GATEWAY_BASE_URL = os.getenv("MODEL_GATEWAY_BASE_URL", "http://10.252.92.98:9050").rstrip("/")

#: 网关凭据（所有模型公用）。APPKEY 无内置值：必须由环境变量注入，
#: 联调值见 docs/参考记录/聊天记录.txt（未入库），生产建议 Secret。
MODEL_APP_ID = os.getenv("MODEL_APP_ID", "audioasr")
MODEL_APP_KEY = os.getenv("MODEL_APP_KEY", "")

MODEL_GATEWAY_TIMEOUT_SECONDS = int(os.getenv("MODEL_GATEWAY_TIMEOUT_SECONDS", "300"))
MODEL_GATEWAY_RETRIES = int(os.getenv("MODEL_GATEWAY_RETRIES", "2"))  # 重试 2 次，即最多调用 3 次

#: 文本模型（体裁判定 / 事实抽取 / 元信息补全 / 公式 LaTeX 校验）：
#: 升级要求 2.3 —— 文本生成选 Qwen3.5-9B。
TEXT_MODEL = os.getenv("TEXT_MODEL", "Qwen3.5-9B")
TEXT_MODEL_PATH = os.getenv("TEXT_MODEL_PATH", "/Qwen3.5-9B")

#: 视觉模型（版面检测 / 公式定位与识别 / 图片判型与描述）：
#: 沿用冒烟验证过的 Qwen3-VL-8B-Instruct 档位，对应网关 PATH（模型清单逐字值）。
VISION_MODEL = os.getenv("VISION_MODEL", "qwen3-vl-8b-instruct")
VISION_MODEL_PATH = os.getenv("VISION_MODEL_PATH", "/qwen3-vl-8b-instruct")

# ==================== SiliconFlow 回退后端 ====================

SILICONFLOW_BASE_URL = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1").rstrip("/")
#: 回退后端的 key 同样只走环境变量（升级要求：凭据不落盘）；本地联调见 operators/.env。
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "")

#: SiliconFlow 侧的模型名（仅在 MODEL_PROVIDER=siliconflow 时生效）；
#: 与升级前一致：文本 DeepSeek-V3.2、视觉 Qwen3-VL-8B-Instruct。
SILICONFLOW_TEXT_MODEL = os.getenv("SILICONFLOW_TEXT_MODEL", "deepseek-ai/DeepSeek-V3.2")
SILICONFLOW_VISION_MODEL = os.getenv("SILICONFLOW_VISION_MODEL", "Qwen/Qwen3-VL-8B-Instruct")

SILICONFLOW_TIMEOUT_SECONDS = 60
SILICONFLOW_RETRIES = 2

# ==================== 统一调用约定（四份交付说明一致口径） ====================

TEMPERATURE = 0.0
DEFAULT_CONCURRENCY = 4  # 算子内并发，可配范围 4-8
MAX_CONCURRENCY = 8

#: 置信度合法区间（模型禁止输出 1.0，越界截断）
CONFIDENCE_MIN = 0.0
CONFIDENCE_MAX = 0.98


def is_idg() -> bool:
    return MODEL_PROVIDER == "idg"


def default_timeout() -> int:
    return MODEL_GATEWAY_TIMEOUT_SECONDS if is_idg() else SILICONFLOW_TIMEOUT_SECONDS


def default_retries() -> int:
    return MODEL_GATEWAY_RETRIES if is_idg() else SILICONFLOW_RETRIES


def text_model() -> str:
    return TEXT_MODEL if is_idg() else SILICONFLOW_TEXT_MODEL


def vision_model() -> str:
    return VISION_MODEL if is_idg() else SILICONFLOW_VISION_MODEL
