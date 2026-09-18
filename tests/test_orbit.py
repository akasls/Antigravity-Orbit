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


if __name__ == "__main__":
    unittest.main()
