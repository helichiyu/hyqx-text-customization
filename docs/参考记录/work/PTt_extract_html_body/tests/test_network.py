"""PTt_extract_html_body 单元测试（unittest，无需 pytest/FastAPI 即可运行）。

运行：python tests/test_network.py   或   python -m unittest tests.test_network -v
"""

from __future__ import annotations

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_OP_DIR = os.path.dirname(_HERE)
_ROOT = os.path.dirname(_OP_DIR)
for _path in (_ROOT, _OP_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from common.operator_base import ACTION_KEEP, ACTION_REMOVE, TextRecord  # noqa: E402
from common.text_records import parse_text_records  # noqa: E402
from model.network import HtmlBodyExtractor, extract_body, strip_to_lines  # noqa: E402

NEWS_HTML = (
    "<html><head><title>测试新闻</title></head><body>"
    "<div>首页</div><div>新闻中心</div><div>登录</div>"
    "<p>国家数据工程建设持续推进，预训练语料库的规模化清洗能力成为关键环节，多方协作的产线已投入试运行。</p>"
    "<p>清洗产线覆盖正文提取、格式归一、去重过滤与质量评估等环节，规则与模型结合保证了处理稳定性。</p>"
    "<p>团队表示后续将扩展多模态语料的统一清洗能力，支撑更大规模的预训练数据供给。</p>"
    "<div>关于我们</div><div>联系方式</div></body></html>"
)

ERROR_HTML = (
    "<html><body><div>首页</div><div>站点地图</div>"
    "<h1>404 NOT FOUND!</h1><p>抱歉，您访问的页面不存在。</p></body></html>"
)


class TestExtractBody(unittest.TestCase):
    def test_news_body_kept_and_chrome_trimmed(self):
        body, is_error = extract_body(NEWS_HTML)
        self.assertFalse(is_error)
        self.assertIn("预训练语料库", body)
        self.assertNotIn("登录", body)
        self.assertNotIn("关于我们", body)

    def test_article_mentioning_404_not_killed(self):
        # 回归：错误页检测改行级匹配——正文提及 404/Not Found 的技术文章不得整篇误杀
        article = ("<html><body><p>当网站返回404错误时，用户会看到Not Found页面，"
                   "这是互联网最常见的状态码之一，工程师需要正确处理这类响应并配置重定向策略。</p></body></html>")
        body, is_error = extract_body(article)
        self.assertFalse(is_error)
        self.assertIn("状态码", body)

    def test_error_page_detected(self):
        body, is_error = extract_body(ERROR_HTML)
        self.assertTrue(is_error)
        self.assertEqual(body, "")

    def test_short_text_skips_density(self):
        body, is_error = extract_body("<html><body><p>这是一段极短的网页正文，包含标点符号。</p></body></html>")
        self.assertFalse(is_error)
        self.assertIn("极短", body)

    def test_interior_short_line_kept(self):
        # 正文内部的短句（带标点）不应被 chrome 剔除
        html_text = (
            "<html><body><div>首页</div>"
            "<p>第一段正文内容较长，讲述数据清洗产线的整体架构与关键指标表现，用于密度检测。</p>"
            "<p>好。</p>"
            "<p>第二段正文内容同样较长，描述规则与模型结合的混合清洗策略与联调验证结论。</p>"
            "<div>版权所有</div></body></html>"
        )
        body, _ = extract_body(html_text)
        self.assertIn("好。", body)

    def test_script_style_removed(self):
        html_text = "<html><head><style>.a{color:red}</style><script>var x=1;</script></head><body><p>正文内容第一句，描述清洗流程的关键步骤与验证方式。</p><p>正文内容第二句，补充说明行块密度算法的参数选择与实测效果。</p></body></html>"
        lines = strip_to_lines(html_text)
        joined = "\n".join(lines)
        self.assertNotIn("color", joined)
        self.assertNotIn("var x", joined)

    def test_interior_chrome_vocab_removed(self):
        # 密度区间内部的独立导航/页脚词行剔除（真实语料 20.4%→2% 残留的改进项）
        body = ("正文第一段较长内容，说明产线架构与指标表现的详细情况，用于密度定位的锚点段落。" * 2
                + "\n关于我们\n"
                + "正文第二段继续描述清洗策略，保证密度平台覆盖内部词行的场景验证。"
                + "\n注册登录\n"
                + "正文第三段补充联调验证结论，进一步稳定密度区间的边界判定。")
        html_text = f"<html><body><div>首页</div><p>{body}</p><div>版权所有</div></body></html>"
        result_text, is_error = extract_body(html_text)
        self.assertFalse(is_error)
        self.assertNotIn("关于我们", result_text)
        self.assertNotIn("注册登录", result_text)
        self.assertIn("密度定位的锚点段落", result_text)

    def test_copyright_signature_line_removed(self):
        # "版权所有:站点名" 署名行剔除
        body = "正文段落内容较长，描述数据工程总体进展与产线落地情况，作为密度锚点使用。" * 2 + "\n版权所有:东方财富网\n结尾正文一句。"
        html_text = f"<html><body><p>{body}</p></body></html>"
        result_text, _ = extract_body(html_text)
        self.assertNotIn("东方财富网", result_text)
        self.assertIn("结尾正文一句", result_text)

    def test_content_with_nav_word_kept(self):
        # 含导航词的正文内容行不得误删（"注册资本"是正文）
        body = ("天眼查App显示，近日某核电有限公司成立，注册资本1亿元人民币，经营范围含技术服务等，股东信息完整披露。" * 2)
        html_text = f"<html><body><p>{body}</p></body></html>"
        result_text, _ = extract_body(html_text)
        self.assertIn("注册资本", result_text)


class TestOperatorProcess(unittest.TestCase):
    def setUp(self):
        self.op = HtmlBodyExtractor()

    def test_process_records(self):
        records = [
            TextRecord("r1", NEWS_HTML),
            TextRecord("r2", ERROR_HTML),
        ]
        output = self.op.process(records)
        self.assertEqual(len(output.results), 2)
        r1, r2 = output.results
        self.assertEqual(r1.action, ACTION_KEEP)
        self.assertIn("预训练语料库", r1.fields["text"])
        self.assertEqual(r2.action, ACTION_REMOVE)
        self.assertEqual(r2.tags, ["原始文件-无法解析"])
        self.assertEqual(r2.fields["reason"], "404/失效页面，无有效正文")

    def test_undecodable_record_flagged(self):
        records = [TextRecord("r_bad", "", {"decodeFailed": True, "parseError": "编码无法识别或转换: gb18030 fail"})]
        output = self.op.process(records)
        result = output.results[0]
        self.assertEqual(result.action, ACTION_REMOVE)
        self.assertEqual(result.errorCode, "DECODE_FAIL")

    def test_demo_jsonl_roundtrip(self):
        import json
        from pathlib import Path

        demo_path = Path(_OP_DIR) / "dataset" / "sample" / "demo.jsonl"
        parsed = parse_text_records(demo_path.read_bytes(), "demo.jsonl")
        self.assertEqual(len(parsed), 3)
        output = self.op.process(parsed)
        self.assertEqual(len(output.results), 3)
        # sample_error_002 应命中错误页
        by_name = {r.fieldName: r for r in output.results}
        self.assertEqual(by_name["sample_error_002"].action, ACTION_REMOVE)
        self.assertEqual(by_name["sample_news_001"].action, ACTION_KEEP)
        # envelope 序列化 smoke
        payload = json.dumps([r.to_dict() for r in output.results], ensure_ascii=False)
        self.assertIn("fieldName", payload)


if __name__ == "__main__":
    unittest.main(verbosity=2)
