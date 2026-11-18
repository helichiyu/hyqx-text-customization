"""PTt_extract_pdf_body 单元测试。

本机无现成带文本层的 PDF 生成库，采用三层策略：
1. parse_page_range 纯函数全测（无需 PDF）
2. 仓库 tests_assets/dirty_corpus_100 里的真实 PDF（有文本层→提取；扫描版→明确报错，两者都是契约内行为）
3. 魔数/参数非法路径
"""

from __future__ import annotations
import os, sys, unittest
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (os.path.dirname(_HERE), os.path.dirname(os.path.dirname(_HERE))):
    if _p not in sys.path: sys.path.insert(0, _p)

from common.operator_base import OperatorContext
from model.network import PdfTextExtractor, parse_page_range

ROOT = Path(_HERE).resolve().parent.parent
PDF_ASSETS = sorted((ROOT / "tests_assets" / "dirty_corpus_100").glob("*.pdf"))


class TestPageRange(unittest.TestCase):
    def test_all(self):
        self.assertEqual(parse_page_range("全部", 5), [0, 1, 2, 3, 4])
        self.assertEqual(parse_page_range("", 3), [0, 1, 2])

    def test_range_and_list(self):
        self.assertEqual(parse_page_range("1-3", 10), [0, 1, 2])
        self.assertEqual(parse_page_range("2,5", 10), [1, 4])
        self.assertEqual(parse_page_range("1-99", 3), [0, 1, 2])  # 越界截断

    def test_invalid(self):
        for bad in ("abc", "3-1", "0", "1-x"):
            with self.assertRaises(ValueError):
                parse_page_range(bad, 10)


class TestExtractor(unittest.TestCase):
    def test_bad_magic(self):
        op = PdfTextExtractor()
        out = op.process([], context=OperatorContext(raw=b"not pdf", filename="a.pdf"))
        r = out.results[0]
        self.assertEqual(r.action, "remove"); self.assertEqual(r.tags, ["原始文件-无法解析"])

    def test_assets_pdf_contract(self):
        """真实 PDF：有文本层→提取成功；扫描版→OCR 未接入的明确报错。两者皆为契约行为。"""
        if not PDF_ASSETS:
            self.skipTest("无 PDF 测试资产")
        op = PdfTextExtractor()
        raw = PDF_ASSETS[0].read_bytes()
        out = op.process([], context=OperatorContext(raw=raw, filename=PDF_ASSETS[0].name))
        r = out.results[0]
        if r.action == "keep":
            self.assertTrue(r.fields["text"].strip())
            self.assertGreaterEqual(r.fields["pages"], 1)
        else:
            self.assertEqual(r.errorCode, "PARSE_FAIL")
            self.assertTrue("OCR" in r.error or "无法解析" in r.error or "文本层" in r.error)


def build_scanned_pdf(text: str = "数据清洗平台扫描版OCR验证文本") -> bytes:
    """生成无文本层的图片型 PDF（PIL 渲染文字→存 PDF 页）。"""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (600, 200), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("msyh.ttc", 32)
    except Exception:
        font = ImageFont.load_default()
    draw.text((30, 80), text, fill="black", font=font)
    import io
    buf = io.BytesIO()
    img.save(buf, format="PDF", resolution=100)
    return buf.getvalue()


class TestOcrFallback(unittest.TestCase):
    def test_scanned_pdf_mocked_ocr(self):
        # 离线：mock 视觉 API，验证 OCR 分支调度与 extractionMethod 标注
        from unittest import mock
        import common.llm_client as llm
        op = PdfTextExtractor()
        scanned = build_scanned_pdf()
        self.assertTrue(scanned.startswith(b"%PDF"))
        with mock.patch.object(llm, "chat_vision", return_value="扫描版OCR验证文本"):
            out = op.process([], context=OperatorContext(raw=scanned, filename="scan.pdf"))
        r = out.results[0]
        self.assertEqual(r.action, "keep")
        self.assertEqual(r.fields["extractionMethod"], "ocr(qwen3-vl)")
        self.assertIn("OCR验证文本", r.fields["text"])

    def test_ocr_disabled_error(self):
        op = PdfTextExtractor()
        scanned = build_scanned_pdf()
        out = op.process([], params={"OCR识别": "关闭"},
                         context=OperatorContext(raw=scanned, filename="scan.pdf"))
        r = out.results[0]
        self.assertEqual(r.errorCode, "PARSE_FAIL")
        self.assertIn("OCR识别=关闭", r.error)

    def test_live_scanned_pdf_ocr(self):
        # 真实 API：Qwen3-VL 识别 PIL 渲染的中文（失败自动 skip）
        op = PdfTextExtractor()
        scanned = build_scanned_pdf("人工智能语料清洗平台扫描件")
        out = op.process([], context=OperatorContext(raw=scanned, filename="scan.pdf"))
        r = out.results[0]
        if r.errorCode == "PARSE_FAIL" and "视觉模型" in (r.error or ""):
            self.skipTest("API 不可用")
        self.assertEqual(r.action, "keep")
        self.assertIn("语料清洗", r.fields["text"])


if __name__ == "__main__":
    unittest.main(verbosity=2)