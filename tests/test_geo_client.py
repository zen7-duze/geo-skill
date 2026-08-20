#!/usr/bin/env python3
"""geo_client 单元测试 —— 纯标准库、不联网、可离线跑。

覆盖的是「改错了会静默坑到用户」的那些点:凭证读写、设备标识不冲掉 token、
免登录路径不带 Authorization、402 不当成错误、金额换算、命令分发。

    python3 tests/test_geo_client.py
"""
import base64
import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
CLIENT = ROOT / "vigilath-geo" / "scripts" / "geo_client.py"


@contextlib.contextmanager
def client_in(home: str, **env):
    """在指定 HOME 下加载全新 client,环境在**整个 with 块**里有效。

    ★ 不能写成「加载时 patch、加载完就恢复」:client 是在调用时才去写
      ~/.vigilath/config,环境一恢复就写到**真实 HOME** 去了 ——
      这个文件自己踩过一次,把开发机的配置目录建了出来。
    """
    envs = {"HOME": home}
    envs.update(env)
    for k in ("VIGILATH_AGENT_TOKEN", "VIGILATH_BASE", "VIGILATH_DEVICE_ID"):
        envs.setdefault(k, "")
    with mock.patch.dict(os.environ, envs, clear=False):
        spec = importlib.util.spec_from_file_location("gc_under_test", CLIENT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        yield mod


class _Resp:
    """够用的假响应:支持 with 和 read()。"""

    def __init__(self, payload):
        self._b = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class ConfigTest(unittest.TestCase):
    def test_reads_config_file(self):
        home = tempfile.mkdtemp()
        os.makedirs(f"{home}/.vigilath")
        Path(f"{home}/.vigilath/config").write_text(
            "# 注释\nVIGILATH_AGENT_TOKEN=tok_abc\nVIGILATH_BASE=https://x.test/api/agent/v1\n",
            encoding="utf-8")
        with client_in(home) as m:
            self.assertEqual(m._conf("VIGILATH_AGENT_TOKEN"), "tok_abc")
            self.assertEqual(m.BASE, "https://x.test/api/agent/v1")

    def test_site_api_derived_from_base(self):
        """免登录端点在站点 API 根下,必须由 BASE 剥掉 /agent/v1 推出来。"""
        with client_in(tempfile.mkdtemp(), VIGILATH_BASE="https://x.test/api/agent/v1") as m:
            self.assertEqual(m.SITE_API, "https://x.test/api")

    def test_missing_token_dies_without_leaking(self):
        with client_in(tempfile.mkdtemp()) as m:
            err = io.StringIO()
            with mock.patch("sys.stderr", err), self.assertRaises(SystemExit):
                m._headers()
            self.assertNotIn("Bearer", err.getvalue())


class DeviceIdTest(unittest.TestCase):
    def test_generated_and_persisted_600(self):
        home = tempfile.mkdtemp()
        with client_in(home) as m:
            d1 = m._device_id()
            self.assertTrue(d1.startswith("dev_"))
            self.assertEqual(d1, m._device_id(), "同一进程内必须稳定")
            self.assertEqual(oct(os.stat(f"{home}/.vigilath/config").st_mode)[-3:], "600")

    def test_does_not_clobber_existing_token(self):
        """生成设备标识会重写 config —— 绝不能把已有凭证冲掉。"""
        home = tempfile.mkdtemp()
        os.makedirs(f"{home}/.vigilath")
        Path(f"{home}/.vigilath/config").write_text(
            "VIGILATH_AGENT_TOKEN=tok_keepme\nVIGILATH_BASE=https://x.test/api/agent/v1\n",
            encoding="utf-8")
        with client_in(home) as m:
            m._device_id()
        body = Path(f"{home}/.vigilath/config").read_text(encoding="utf-8")
        self.assertIn("VIGILATH_AGENT_TOKEN=tok_keepme", body)
        self.assertIn("VIGILATH_DEVICE_ID=dev_", body)

    def test_survives_unwritable_home(self):
        """写不了配置也不能崩 —— 服务端还有出口 IP 那道闸。"""
        with client_in("/proc/nonexistent-readonly") as m:
            self.assertTrue(m._device_id().startswith("dev_"))


class AnonymousPathTest(unittest.TestCase):
    """免登录命令绝不能带 Authorization —— 带了就变成要授权,免登录就废了。"""

    def _seen(self, m, call):
        seen = {}

        def fake_request(req, timeout=30):
            seen["headers"] = {k.lower(): v for k, v in req.headers.items()}
            seen["url"] = req.full_url
            return _Resp({"url": "u", "score": 1, "grade": "A", "checks": [],
                          "summary": {}, "industries": []})

        with mock.patch.object(m, "_request", fake_request):
            call()
        return seen

    def test_check_has_no_auth_header(self):
        with client_in(tempfile.mkdtemp(), VIGILATH_AGENT_TOKEN="tok_x") as m:
            seen = self._seen(m, lambda: m.check("https://example.com", include_seo=False))
            self.assertNotIn("authorization", seen["headers"])
            self.assertIn("/check/anonymous", seen["url"])

    def test_industry_has_no_auth_header(self):
        with client_in(tempfile.mkdtemp(), VIGILATH_AGENT_TOKEN="tok_x") as m:
            seen = self._seen(m, lambda: m.industry())
            self.assertNotIn("authorization", seen["headers"])


class PaymentTest(unittest.TestCase):
    def test_402_is_not_an_error(self):
        """402 是充值流程里的正常一步(带着付款要求),不能当异常抛出去。"""
        with client_in(tempfile.mkdtemp(), VIGILATH_AGENT_TOKEN="tok_x") as m:
            payload = json.dumps({"x402Version": 1, "accepts": [{"payTo": "0xabc"}]}).encode()
            err = urllib.error.HTTPError("u", 402, "Payment Required", {}, io.BytesIO(payload))
            with mock.patch.object(m, "_request", side_effect=err):
                out = m.topup("100")
            self.assertEqual(out["accepts"][0]["payTo"], "0xabc")
            self.assertIn("_hint", out, "要告诉 agent 这不是失败、下一步做什么")

    def test_tx_hash_goes_in_x_payment_header(self):
        with client_in(tempfile.mkdtemp(), VIGILATH_AGENT_TOKEN="tok_x") as m:
            seen = {}

            def fake_request(req, timeout=30):
                seen.update({k.lower(): v for k, v in req.headers.items()})
                seen["body"] = req.data
                return _Resp({"status": "ok"})

            with mock.patch.object(m, "_request", fake_request):
                m.topup("72", tx_hash="0xdeadbeef")
            self.assertEqual(json.loads(base64.b64decode(seen["x-payment"]))["tx_hash"], "0xdeadbeef")
            self.assertEqual(json.loads(seen["body"])["amount_cents"], 7200, "元 → 分")

    def test_amount_rejects_non_numeric(self):
        with client_in(tempfile.mkdtemp(), VIGILATH_AGENT_TOKEN="tok_x") as m:
            with mock.patch("sys.stderr", io.StringIO()), self.assertRaises(SystemExit):
                m.topup("一百块")


class CheckShapeTest(unittest.TestCase):
    def test_half_aggregates_by_category(self):
        with client_in(tempfile.mkdtemp()) as m:
            raw = {"url": "u", "score": 28, "grade": "F", "summary": {},
                   "checks": [{"category": "HTTPS", "status": "PASS", "message": "ok"},
                              {"category": "Meta Tags", "status": "FAIL", "message": "缺 description"},
                              {"category": "Meta Tags", "status": "WARN", "message": "标题过长"}],
                   "locked_categories": ["llms.txt", "Schema"]}
            with mock.patch.object(m, "_request", lambda req, timeout=30: _Resp(raw)):
                out = m.check("https://example.com", include_seo=False)
            geo = out["geo"]
            self.assertEqual(geo["score"], 28)
            self.assertEqual(geo["visible_categories"]["Meta Tags"]["fail"], 1)
            self.assertEqual(geo["visible_categories"]["Meta Tags"]["warn"], 1)
            self.assertEqual(geo["locked_count"], 2, "锁住的类目要报数量,让 agent 知道没看全")
            self.assertIn("note", out)


class CliTest(unittest.TestCase):
    def test_unknown_command_exits(self):
        with client_in(tempfile.mkdtemp()) as m:
            with mock.patch("sys.stderr", io.StringIO()), self.assertRaises(SystemExit):
                m.main(["geo_client.py", "nosuchcmd"])

    def test_check_requires_url(self):
        with client_in(tempfile.mkdtemp()) as m:
            with mock.patch("sys.stderr", io.StringIO()), self.assertRaises(SystemExit):
                m.main(["geo_client.py", "check"])

    def test_usage_lists_免登录_first(self):
        """用法提示里免登录命令排在前面 —— agent 读到的第一眼决定它先试哪个。"""
        with client_in(tempfile.mkdtemp()) as m:
            err = io.StringIO()
            with mock.patch("sys.stderr", err), self.assertRaises(SystemExit):
                m.main(["geo_client.py"])
            usage = err.getvalue()
            self.assertLess(usage.index("check"), usage.index("chat"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
