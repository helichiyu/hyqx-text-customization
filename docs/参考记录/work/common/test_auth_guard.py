"""auth_guard 单元测试：python common/test_auth_guard.py（无需 FastAPI）。"""

from __future__ import annotations

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_HERE)
for _p in (_PARENT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from common import auth_guard


class AuthGuardTest(unittest.TestCase):
    def setUp(self):
        self._saved = {
            key: os.environ.pop(key, None)
            for key in (auth_guard.DIGEST_ENV, auth_guard.PLAIN_ENV)
        }

    def tearDown(self):
        for key, value in self._saved.items():
            if value is not None:
                os.environ[key] = value

    def test_disabled_when_unset(self):
        """未配置令牌：拦截关闭，任意请求放行（开发模式）。"""
        self.assertFalse(auth_guard.auth_enabled())
        self.assertEqual(auth_guard.expected_digests(), [])
        ok, status, _ = auth_guard.verify("anything")
        self.assertTrue(ok)

    def test_digest_env(self):
        """摘要变量：正确令牌放行；错误 403；缺失 401。"""
        os.environ[auth_guard.DIGEST_ENV] = auth_guard._digest("令牌A")
        self.assertTrue(auth_guard.auth_enabled())
        ok, status, _ = auth_guard.verify("令牌A")
        self.assertTrue(ok)
        ok, status, msg = auth_guard.verify("错误令牌")
        self.assertFalse(ok)
        self.assertEqual(status, 403)
        ok, status, msg = auth_guard.verify(None)
        self.assertFalse(ok)
        self.assertEqual(status, 401)

    def test_plain_env(self):
        """明文变量（联调）：等价于其摘要。"""
        os.environ[auth_guard.PLAIN_ENV] = "联调令牌"
        ok, status, _ = auth_guard.verify("联调令牌")
        self.assertTrue(ok)
        ok, status, _ = auth_guard.verify("别的")
        self.assertFalse(ok)

    def test_digest_env_takes_priority(self):
        """摘要变量与明文变量同时设置时摘要优先。"""
        os.environ[auth_guard.DIGEST_ENV] = auth_guard._digest("正式令牌")
        os.environ[auth_guard.PLAIN_ENV] = "联调令牌"
        ok, _, _ = auth_guard.verify("正式令牌")
        self.assertTrue(ok)
        ok, status, _ = auth_guard.verify("联调令牌")
        self.assertFalse(ok)

    def test_multiple_digests(self):
        """多摘要（多调用方各持一个令牌）：任一匹配即放行。"""
        os.environ[auth_guard.DIGEST_ENV] = (
            f"{auth_guard._digest('甲方令牌')}, {auth_guard._digest('乙方令牌')}"
        )
        for token in ("甲方令牌", "乙方令牌"):
            ok, _, _ = auth_guard.verify(token)
            self.assertTrue(ok)
        ok, _, _ = auth_guard.verify("第三方令牌")
        self.assertFalse(ok)

    def test_token_from_headers(self):
        """X-Token 优先于 token 头；空白令牌视为缺失。"""
        self.assertEqual(auth_guard.token_from({"x-token": " a "}), "a")
        self.assertEqual(auth_guard.token_from({"token": "b"}), "b")
        self.assertEqual(
            auth_guard.token_from({"x-token": "a", "token": "b"}), "a"
        )
        self.assertIsNone(auth_guard.token_from({}))
        self.assertIsNone(auth_guard.token_from({"x-token": "  "}))

    def test_whitelist(self):
        """仅 /health（含尾部斜杠）放行。"""
        self.assertTrue(auth_guard.is_whitelisted("/health"))
        self.assertTrue(auth_guard.is_whitelisted("/health/"))
        self.assertFalse(auth_guard.is_whitelisted("/predict"))
        self.assertFalse(auth_guard.is_whitelisted("/docs"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
