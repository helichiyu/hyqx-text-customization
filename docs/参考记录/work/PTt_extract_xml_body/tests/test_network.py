"""PTt_extract_xml_body 单元测试。"""

from __future__ import annotations
import os, sys, unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (os.path.dirname(_HERE), os.path.dirname(os.path.dirname(_HERE))):
    if _p not in sys.path: sys.path.insert(0, _p)

from common.operator_base import TextRecord
from model.network import XmlBodyExtractor, extract_xml_text

XML = ('<?xml version="1.0" encoding="UTF-8"?>'
       "<病历><主诉>患者间断头痛三年。</主诉>"
       "<诊断 result=\"阳性\">偏头痛可能性大。</诊断>"
       "<备注>随诊记录。</备注></病历>")


class TestXml(unittest.TestCase):
    def test_full_text(self):
        text = extract_xml_text(XML, None, True)
        self.assertIn("间断头痛", text); self.assertIn("偏头痛", text)
        self.assertNotIn("<主诉>", text); self.assertNotIn("result=", text)

    def test_scope_node(self):
        text = extract_xml_text(XML, "诊断", True)
        self.assertIn("偏头痛", text); self.assertNotIn("头痛三年", text)

    def test_scope_missing(self):
        with self.assertRaises(ValueError):
            extract_xml_text(XML, "不存在的节点", True)

    def test_tag_filter_disabled_keeps_raw(self):
        text = extract_xml_text(XML, None, False)
        self.assertIn("<主诉>", text); self.assertNotIn("<?xml", text)

    def test_process_scope_param(self):
        op = XmlBodyExtractor()
        out = op.process([TextRecord("r1", XML)], params={"正文提取范围": "主诉"})
        r = out.results[0]
        self.assertEqual(r.action, "keep"); self.assertIn("头痛", r.fields["text"])

    def test_invalid_xml_removed(self):
        op = XmlBodyExtractor()
        out = op.process([TextRecord("bad", "<unclosed>没有闭合")])
        r = out.results[0]
        self.assertEqual(r.action, "remove"); self.assertEqual(r.tags, ["原始文件-无法解析"])
        self.assertEqual(r.errorCode, "PARSE_FAIL")


if __name__ == "__main__":
    unittest.main(verbosity=2)
