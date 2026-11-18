"""PTt_extract_docx_body 单元测试（用 python-docx 现场构造测试文档）。"""

from __future__ import annotations
import io, os, sys, unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (os.path.dirname(_HERE), os.path.dirname(os.path.dirname(_HERE))):
    if _p not in sys.path: sys.path.insert(0, _p)

from common.operator_base import OperatorContext
from model.network import DocxTextExtractor, extract_docx_text

try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


def build_docx() -> bytes:
    doc = Document()
    doc.add_paragraph("数据清洗产线的总体架构。")
    doc.add_paragraph("规则与模型结合的混合清洗策略。")
    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "指标"; table.cell(0, 1).text = "数值"
    table.cell(1, 0).text = "留存率"; table.cell(1, 1).text = "95%"
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


@unittest.skipUnless(HAS_DOCX, "python-docx 未安装")
class TestDocx(unittest.TestCase):
    def setUp(self):
        self.raw = build_docx()

    def test_extract_with_table(self):
        text = extract_docx_text(self.raw, keep_tables=True, keep_comments=False, keep_hyperlinks=False)
        self.assertIn("总体架构", text); self.assertIn("混合清洗策略", text)
        self.assertIn("留存率 | 95%", text)

    def test_extract_without_table(self):
        text = extract_docx_text(self.raw, keep_tables=False, keep_comments=False, keep_hyperlinks=False)
        self.assertIn("总体架构", text); self.assertNotIn("留存率", text)

    def test_process_keep_tables(self):
        op = DocxTextExtractor()
        out = op.process([], context=OperatorContext(raw=self.raw, filename="sample.docx"))
        r = out.results[0]
        self.assertEqual(r.action, "keep")
        self.assertIn("留存率", r.fields["text"])

    def test_process_drop_tables_param(self):
        op = DocxTextExtractor()
        out = op.process([], params={"表格内容": "删除"},
                         context=OperatorContext(raw=self.raw, filename="sample.docx"))
        self.assertNotIn("留存率", out.results[0].fields["text"])

    def test_bad_magic(self):
        op = DocxTextExtractor()
        out = op.process([], context=OperatorContext(raw=b"PK_corrupted_not_zip", filename="a.docx"))
        r = out.results[0]
        self.assertEqual(r.action, "remove"); self.assertEqual(r.errorCode, "PARSE_FAIL")


class TestBadInputAlways(unittest.TestCase):
    def test_not_docx_container(self):
        op = DocxTextExtractor()
        out = op.process([], context=OperatorContext(raw=b"plain text", filename="a.docx"))
        self.assertEqual(out.results[0].tags, ["原始文件-无法解析"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
