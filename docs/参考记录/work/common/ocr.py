"""扫描版 PDF 的 OCR 管线（#5/#8 共用，走统一 LLM 网关）。

链路：pypdfium2 渲染页 → PNG(base64) → Qwen3-VL-8B-Instruct（硅基流动 API，
与内部自部署同款）逐页提文 → 按页拼接。

依赖：pypdfium2（Apache/BSD 许可）。缺失或 API 失败时抛出明确异常，
由调用方转为 PARSE_FAIL 口径（不静默输出空文档）。
"""

from __future__ import annotations

import base64
import io
from typing import List, Optional, Tuple

from common import llm_client as llm

DEFAULT_OCR_PROMPT = (
    "提取图片中的全部文字内容，保持原有阅读顺序与分段，"
    "只输出文字本身，不要任何解释说明。"
)
RENDER_SCALE = 2.0   # ≈144 DPI，中文清晰可辨；放大增加耗时与 token


def _render_pages(pdf_bytes: bytes, page_indexes: Optional[List[int]]) -> List["object"]:
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(pdf_bytes)
    indexes = page_indexes if page_indexes is not None else range(len(pdf))
    pages = [pdf[i] for i in indexes]
    return pages


def ocr_pdf(pdf_bytes: bytes, page_indexes: Optional[List[int]] = None,
            prompt: str = DEFAULT_OCR_PROMPT) -> Tuple[str, int]:
    """扫描 PDF → 文本。返回 (文本, OCR 页数)。

    - 页级失败即中止并抛 LlmApiError（半成品文本不可信）
    - 无有效页（空 PDF）返回 ("", 0)
    """
    try:
        import pypdfium2 as pdfium  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("OCR 需要 pypdfium2（页面渲染）——镜像 requirements 已含") from exc

    pages = _render_pages(pdf_bytes, page_indexes)
    if not pages:
        return "", 0
    texts: List[str] = []
    for page in pages:
        bitmap = page.render(scale=RENDER_SCALE)
        image = bitmap.to_pil()
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        content = llm.chat_vision([b64], prompt)
        text = content.strip()
        if text:
            texts.append(text)
    return "\n\n".join(texts), len(pages)
