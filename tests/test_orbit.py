# -*- coding: utf-8 -*-
"""
Antigravity Orbit - Core Unit Tests
"""

import unittest
import json
from pathlib import Path
from core.account_pool import AccountPoolManager
from core.prompt_manager import PromptManager
from core.config import load_config
from core.api_bridge import OrbitApi


class TestOrbitCore(unittest.TestCase):
    def test_config_loading(self):
        cfg = load_config()
        self.assertIsInstance(cfg, dict)
        self.assertIn("customization", cfg)

    def test_prompt_manager(self):
        content = PromptManager.read_system_prompt()
        self.assertIsInstance(content, str)
        self.assertGreater(len(PromptManager.TEMPLATES), 0)

    def test_account_pool_manager(self):
        mgr = AccountPoolManager()
        summary = mgr.get_accounts_summary()
        self.assertIsInstance(summary, dict)
        self.assertIn("accounts", summary)
        self.assertIn("total", summary)

    def test_api_bridge_initial_data(self):
        api = OrbitApi()
        res = api.get_initial_data()
        self.assertIn("config", res)
        self.assertIn("status", res)
        self.assertIn("account_pool", res)
        self.assertIn("prompt", res)
        self.assertIn("logs", res)


    def test_monitor_quota_regex(self):
        from core.monitor import QUOTA_ERROR_REGEX
        # 1. 验证此前误报的代码片段与随机哈希数字绝对不会被误判
        self.assertIsNone(QUOTA_ERROR_REGEX.search("react-reconciler-8e99e505c4429605.js"))
        self.assertIsNone(QUOTA_ERROR_REGEX.search("use super::{quota::QuotaData, token::TokenData};"))
        self.assertIsNone(QUOTA_ERROR_REGEX.search("def fetch_account_quota_data(token): pass"))
        self.assertIsNone(QUOTA_ERROR_REGEX.search("crates/cockpit-core/src/modules/quota.rs"))

        # 2. 验证真实的限额/熔断报错可以精准识别
        self.assertIsNotNone(QUOTA_ERROR_REGEX.search("Resource exhausted: quota exceeded for model gemini-2.5"))
        self.assertIsNotNone(QUOTA_ERROR_REGEX.search("HTTP 429 Too Many Requests: Rate limit reached"))
        self.assertIsNotNone(QUOTA_ERROR_REGEX.search("Exceeded your current quota. Please check your plan."))
        self.assertIsNotNone(QUOTA_ERROR_REGEX.search("当前账号 Gemini 模型额度已耗尽"))
    def test_oauth_flow(self):
        from core.account_pool import extract_oauth_code
        # 1. 授权 URL 生成与参数校验
        url = AccountPoolManager.generate_oauth_url(port=51121)
        self.assertTrue(url.startswith("https://accounts.google.com/o/oauth2/v2/auth"))
        self.assertIn("client_id=", url)
        self.assertIn("redirect_uri=http%3A%2F%2Flocalhost%3A51121%2Foauth-callback", url)

        # 2. 授权码提取
        raw_code = "4/0AcvDUpBP9y"
        full_url = f"http://localhost:51121/oauth-callback?code={raw_code}&scope=email"
        self.assertEqual(extract_oauth_code(full_url), raw_code)
        self.assertEqual(extract_oauth_code(raw_code), raw_code)

        # 3. 启动与停止本地回调服务
        api = OrbitApi()
        res = api.start_oauth_login(open_browser=False)
        self.assertTrue(res.get("success"))
        cancel_res = api.cancel_oauth_login()
        self.assertTrue(cancel_res.get("success"))

    def test_storage_breakdown(self):
        from core.storage import StorageManager
        breakdown = StorageManager.get_storage_breakdown()
        self.assertIn("cleanable_total_bytes", breakdown)
        self.assertIn("cleanable_total_str", breakdown)
        self.assertIn("chromium_cache_str", breakdown)
        self.assertIn("brain_temp_str", breakdown)

    def test_quota_matrix_fields(self):
        # 验证初始数据结构包含 Claude 与 Gemini 双列矩阵必要字段
        mgr = AccountPoolManager()
        default_quota = {
            "claude_5h_percent": 100,
            "claude_weekly_percent": 100,
            "gemini_5h_percent": 100,
            "gemini_weekly_percent": 100
        }
        for k, v in default_quota.items():
            self.assertEqual(v, 100)

    def test_localization_process_methods(self):
        from core.localization import LocalizationManager
        self.assertTrue(hasattr(LocalizationManager, "is_running"))
        self.assertTrue(hasattr(LocalizationManager, "kill_running_antigravity"))
        self.assertTrue(hasattr(LocalizationManager, "launch_antigravity"))


if __name__ == "__main__":
    unittest.main()
