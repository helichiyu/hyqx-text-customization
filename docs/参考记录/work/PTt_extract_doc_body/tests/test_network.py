"""PTt_extract_doc_body 单元测试。

LibreOffice 转换依赖环境安装 soffice（镜像内已装，本机多数没有）：
- 魔数/参数路径全测
- soffice 存在时做真实转换往返，不存在时验证明确报错
"""

from __future__ import annotations
import os, shutil, sys, unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (os.path.dirname(_HERE), os.path.dirname(os.path.dirname(_HERE))):
    if _p not in sys.path: sys.path.insert(0, _p)

from common.operator_base import OperatorContext
from model.network import DocTextExtractor

DOC_MAGIC = bytes.fromhex("D0CF11E0A1B11AE1")
HAS_SOFFICE = bool(shutil.which("soffice") or shutil.which("libreoffice"))


class TestDoc(unittest.TestCase):
    def test_bad_magic(self):
        op = DocTextExtractor()
        out = op.process([], context=OperatorContext(raw=b"plain text", filename="a.doc"))
        r = out.results[0]
        self.assertEqual(r.action, "remove"); self.assertEqual(r.tags, ["原始文件-无法解析"])
        self.assertIn("文件头不合法", r.error)

    def test_magic_but_no_soffice_clear_error(self):
        if HAS_SOFFICE:
            self.skipTest("本机有 LibreOffice，跳过缺失报错路径")
        op = DocTextExtractor()
        out = op.process([], context=OperatorContext(raw=DOC_MAGIC + b"fake-body", filename="a.doc"))
        r = out.results[0]
        self.assertEqual(r.action, "remove")
        self.assertIn("LibreOffice", r.error)  # 明确指出缺什么，而不是含糊失败

    @unittest.skipUnless(HAS_SOFFICE, "本机无 LibreOffice")
    def test_real_conversion(self):
        # 真实 .doc 往返需要二进制样本；tests_assets 有 .doc 时跑契约测试
        from pathlib import Path

        root = Path(_HERE).resolve().parent.parent
        docs = sorted((root / "tests_assets" / "dirty_corpus_100").glob("*.doc"))
        if not docs:
            self.skipTest("无 .doc 测试资产")
        op = DocTextExtractor()
        raw = docs[0].read_bytes()
        out = op.process([], context=OperatorContext(raw=raw, filename=docs[0].name))
        r = out.results[0]
        self.assertIn(r.action, ("keep", "remove"))  # 契约：不崩溃，必有明确终态
        if r.action == "keep":
            self.assertTrue(r.fields["text"].strip())


if __name__ == "__main__":
    unittest.main(verbosity=2)
