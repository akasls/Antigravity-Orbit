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

    def test_custom_prompt_templates(self):
        import tempfile
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            prompt_file = temp_path / "AGENTS.md"
            backup_file = temp_path / "AGENTS.md.bak"
            templates_file = temp_path / "prompt_templates.json"

            with patch.object(PromptManager, "PROMPT_DIR", temp_path), \
                 patch.object(PromptManager, "PROMPT_FILE", prompt_file), \
                 patch.object(PromptManager, "BACKUP_FILE", backup_file), \
                 patch.object(PromptManager, "TEMPLATES_FILE", templates_file):

                # 1. 获取列表
                templates = PromptManager.get_custom_templates()
                self.assertIsInstance(templates, list)

                # 2. 新增模版
                ok, msg, tpl = PromptManager.save_custom_template("Unit Test Template", "You are a test assistant.")
                self.assertTrue(ok)
                self.assertIn("id", tpl)
                tpl_id = tpl["id"]

                # 3. 编辑模版
                ok2, msg2, tpl2 = PromptManager.save_custom_template("Unit Test Template Updated", "Updated test content.", tpl_id)
                self.assertTrue(ok2)
                self.assertEqual(tpl2["title"], "Unit Test Template Updated")

                # 4. 一键应用模版
                ok3, msg3, applied_content = PromptManager.apply_custom_template(tpl_id)
                self.assertTrue(ok3)
                self.assertEqual(applied_content, "Updated test content.")
                self.assertTrue(prompt_file.exists())
                self.assertEqual(prompt_file.read_text(encoding="utf-8").strip(), "Updated test content.")

                # 5. 删除模版
                ok4, msg4 = PromptManager.delete_custom_template(tpl_id)
                self.assertTrue(ok4)

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
        # 验证初始数据结构包含 Claude 与 Gemini 双列矩阵及下次重置时间与模型明细必要字段
        mgr = AccountPoolManager()
        default_quota = {
            "claude_5h_percent": 100,
            "claude_5h_reset": "2026-09-18T19:52:33Z",
            "claude_weekly_percent": 100,
            "claude_weekly_reset": "2026-09-25T14:52:33Z",
            "gemini_5h_percent": 100,
            "gemini_5h_reset": "2026-09-18T19:52:33Z",
            "gemini_weekly_percent": 100,
            "gemini_weekly_reset": "2026-09-25T14:52:33Z",
            "models": {
                "claude-sonnet-4-6": {"displayName": "Claude Sonnet 4.6", "percent": 100, "resetTime": "2026-09-18T19:52:35Z"},
                "gemini-3.1-pro-high": {"displayName": "Gemini 3.1 Pro", "percent": 100, "resetTime": "2026-09-18T19:52:35Z"}
            }
        }
        self.assertEqual(default_quota["claude_5h_percent"], 100)
        self.assertTrue("Z" in default_quota["claude_5h_reset"])
        self.assertIn("claude-sonnet-4-6", default_quota["models"])
        self.assertIn("gemini-3.1-pro-high", default_quota["models"])

    def test_localization_process_methods(self):
        from core.localization import LocalizationManager
        self.assertTrue(hasattr(LocalizationManager, "is_running"))
        self.assertTrue(hasattr(LocalizationManager, "kill_running_antigravity"))
        self.assertTrue(hasattr(LocalizationManager, "launch_antigravity"))

    def test_proxy_url_auto_assembly(self):
        from core.config import save_config, load_config
        cfg = load_config()
        cfg["customization"]["proxy_host"] = "127.0.0.1"
        cfg["customization"]["proxy_port"] = 7890
        cfg["customization"]["proxy_type"] = "socks5"
        save_config(cfg)
        reloaded = load_config()
        self.assertEqual(reloaded["customization"]["proxy_url"], "socks5://127.0.0.1:7890")

    def test_proxy_test_api(self):
        api = OrbitApi()
        res = api.test_proxy("http", "127.0.0.1", 65530)
        self.assertIsInstance(res, dict)
        self.assertIn("success", res)
        self.assertFalse(res["success"])

    def test_detect_local_proxy(self):
        api = OrbitApi()
        res = api.detect_local_proxy()
        self.assertIsInstance(res, dict)
        self.assertIn("detected", res)

    def test_cockpit_json_extraction(self):
        # 验证多样化 Cockpit Tools 导出格式的提取准确性
        from unittest.mock import patch
        mgr = AccountPoolManager()
        # 1. 数组格式提取
        array_input = json.dumps([{
            "client_id": "test.apps.googleusercontent.com",
            "token": {"access_token": "ya29.test", "refresh_token": "1//test"}
        }])
        with patch.object(AccountPoolManager, "refresh_google_token", return_value=(False, None, "Mocked token invalid")):
            ok, _, msg = mgr.add_account_by_token(array_input)
            self.assertFalse(ok)
            self.assertTrue("Token" in msg or "Mocked" in msg)

    def test_export_and_import_accounts(self):
        api = OrbitApi()
        # 测试 Cockpit 兼容格式导出 (默认)
        res_cockpit = api.export_accounts_data(format_type="cockpit")
        self.assertTrue(res_cockpit.get("success"))
        self.assertIn("json_str", res_cockpit)
        self.assertIsInstance(res_cockpit.get("count"), int)
        parsed_cockpit = json.loads(res_cockpit["json_str"])
        self.assertIsInstance(parsed_cockpit, list)

        # 测试完整备份格式导出
        res_full = api.export_accounts_data(format_type="full")
        self.assertTrue(res_full.get("success"))
        parsed_full = json.loads(res_full["json_str"])
        self.assertIn("accounts", parsed_full)
        self.assertIn("version", parsed_full)

    def test_quota_calculation_variations(self):
        from core.account_pool import AccountPoolManager
        from unittest.mock import patch

        # 1. 模拟正常消耗 (如 42% 与 85%)
        mock_resp_normal = {
            "models": {
                "gemini-2.5-pro": {"displayName": "Gemini 2.5 Pro", "remainingFraction": 0.42, "resetTime": "2026-09-19T18:00:00Z"},
                "claude-3-5-sonnet": {"displayName": "Claude 3.5 Sonnet", "remainingFraction": 0.85, "resetTime": "2026-09-19T18:00:00Z"}
            }
        }
        with patch.object(AccountPoolManager, "_make_request", return_value=(200, mock_resp_normal, "")):
            q = AccountPoolManager.fetch_account_quota_data("fake_token")
            self.assertEqual(q["gemini_5h_percent"], 42)
            self.assertEqual(q["claude_5h_percent"], 85)
            self.assertEqual(q["status"], "HEALTHY")

        # 2. 模拟配额彻底耗尽 0%
        mock_resp_exhausted = {
            "models": {
                "gemini-2.5-pro": {"displayName": "Gemini 2.5 Pro", "remainingFraction": 0.0, "resetTime": "2026-09-19T18:00:00Z"},
                "claude-3-5-sonnet": {"displayName": "Claude 3.5 Sonnet", "remainingFraction": 0.0, "resetTime": "2026-09-19T18:00:00Z"}
            }
        }
        with patch.object(AccountPoolManager, "_make_request", return_value=(200, mock_resp_exhausted, "")):
            q = AccountPoolManager.fetch_account_quota_data("fake_token")
            self.assertEqual(q["gemini_5h_percent"], 0)
            self.assertEqual(q["claude_5h_percent"], 0)
            self.assertEqual(q["status"], "EXHAUSTED")

        # 3. 模拟凭据过期 401
        with patch.object(AccountPoolManager, "_make_request", return_value=(401, {}, "Unauthorized")):
            q = AccountPoolManager.fetch_account_quota_data("fake_token")
            self.assertEqual(q["status"], "EXPIRED")

    def test_notifiers_formatting(self):
        from notifiers import get_active_notifiers

        cfg = {
            "channels": {
                "telegram": {"enabled": True, "bot_token": "123", "chat_id": "456"},
                "feishu": {"enabled": True, "webhook_url": "https://open.feishu.cn/hook/123"},
                "wecom": {"enabled": True, "webhook_url": "https://qyapi.weixin.qq.com/hook/123"}
            }
        }
        notifiers = get_active_notifiers(cfg)
        self.assertEqual(len(notifiers), 3)
        names = {n.name for n in notifiers}
        self.assertEqual(names, {"telegram", "feishu", "wecom"})

    def test_dom_selectors_integrity(self):
        import re
        html = Path("core/web/index.html").read_text(encoding="utf-8")
        js = Path("core/web/app.js").read_text(encoding="utf-8")
        ids_in_js = set(re.findall(r"getElementById\(['\"]([^'\"]+)['\"]\)", js))
        ids_in_js.update(re.findall(r"querySelector(?:All)?\(['\"]#([a-zA-Z0-9_\-]+)['\"]\)", js))
        ids_in_html = set(re.findall(r'id=["\']([^"\']+)["\']', html))
        dynamic_prefixes = ("drawer-", "tag-", "filter-opt-", "acc-card-", "btn-del-", "btn-switch-", "btn-refresh-", "badge-", "model-")
        missing = [i for i in ids_in_js if i not in ids_in_html and not any(i.startswith(p) for p in dynamic_prefixes)]
        self.assertEqual(missing, [], f"Missing DOM IDs: {missing}")

    def test_app_js_runtime_execution(self):
        """测试 app.js 在无头 JS 引擎下执行 renderAll 与各工作区切换，确保无 ReferenceError"""
        import subprocess
        js_test = """
const fs = require('fs');
const code = fs.readFileSync('core/web/app.js', 'utf-8');
const vm = require('vm');
const dummyEl = {
  addEventListener: () => {},
  querySelector: () => dummyEl,
  querySelectorAll: () => [dummyEl],
  classList: { add: () => {}, remove: () => {} },
  value: '',
  textContent: '',
  innerHTML: '',
  style: {},
  checked: false,
  appendChild: () => {},
  getAttribute: () => 'accounts'
};
const context = {
  window: {},
  document: {
    getElementById: () => dummyEl,
    querySelectorAll: () => [dummyEl],
    querySelector: () => dummyEl,
    createElement: () => dummyEl,
    addEventListener: () => {}
  },
  console: console,
  setTimeout: () => {},
  setInterval: () => {},
  clearInterval: () => {},
  clearTimeout: () => {},
  Math: Math,
  Date: Date,
  JSON: JSON,
  parseInt: parseInt,
  parseFloat: parseFloat,
  encodeURIComponent: encodeURIComponent,
  decodeURIComponent: decodeURIComponent
};
context.window = context;
context.addEventListener = () => {};
vm.createContext(context);
vm.runInContext(code, context);
context.appState = {
  config: { customization: {}, channels: {} },
  status: {},
  account_pool: { accounts: [{ id: '1', email: 'test@gmail.com', quota: { tier: 'pro', claude_5h_percent: 100, claude_weekly_percent: 90, gemini_5h_percent: 100, gemini_weekly_percent: 80 } }], healthy: 1, low_or_exhausted: 0 },
  prompt: { content: 'test', templates: [{ id: 'tpl-1', title: 'Tpl 1', content: 'test content' }] }
};
context.renderAll();
context.switchToTab('accounts');
context.switchToTab('perf_localization');
context.switchToTab('rules_prompts');
context.switchToTab('proxy');
context.switchToTab('healing');
context.switchToTab('settings');
"""
        res = subprocess.run(["node", "-e", js_test], capture_output=True, text=True, cwd=str(Path(__file__).parent.parent))
        self.assertEqual(res.returncode, 0, f"app.js execution failed: {res.stderr}")

    def test_api_bridge_extended(self):
        from unittest.mock import patch
        from core.localization import LocalizationManager
        from core.storage import StorageManager
        from core.autostart import AutostartManager
        import webbrowser
        import os

        api = OrbitApi()

        # 1. open_external
        with patch.object(webbrowser, "open", return_value=True) as mock_open:
            res = api.open_external("https://example.com")
            self.assertTrue(res.get("success"))
            mock_open.assert_called_once_with("https://example.com")

        # 2. open_config_dir
        with patch.object(os, "startfile", return_value=True) as mock_start:
            res = api.open_config_dir()
            self.assertTrue(res.get("success"))
            self.assertTrue(mock_start.called)

        # 3. reset_antigravity_full
        with patch.object(LocalizationManager, "kill_running_antigravity", return_value=True), \
             patch.object(LocalizationManager, "restore", return_value=(True, "Restored")), \
             patch.object(StorageManager, "clean_storage", return_value=(0, {})):
            res = api.reset_antigravity_full()
            self.assertTrue(res.get("success"))
            self.assertIn("彻底初始化", res.get("message", ""))

        # 4. save_and_restart
        with patch.object(LocalizationManager, "kill_running_antigravity", return_value=True), \
             patch.object(LocalizationManager, "install", return_value=(True, "Installed")), \
             patch.object(LocalizationManager, "launch_antigravity", return_value=(True, "Launched")):
            test_cfg = {
                "customization": {"language": "zh-CN", "opt_gpu": True},
                "channels": {}
            }
            res = api.save_and_restart(test_cfg)
            self.assertTrue(res.get("success"))
            self.assertIn("已保存", res.get("message", ""))

        # 5. toggle_app_autostart
        with patch.object(AutostartManager, "enable_app_autostart", return_value=(True, "OK")):
            res = api.toggle_app_autostart(True)
            self.assertTrue(res.get("success"))

        # 6. clean_storage
        with patch.object(StorageManager, "clean_storage", return_value=(1024, {"cleaned": True})):
            res = api.clean_storage()
            self.assertTrue(res.get("success"))

    def test_tg_config_migration(self):
        import tempfile
        from unittest.mock import patch
        from core.config import load_config

        with tempfile.TemporaryDirectory() as td:
            cand_file = Path(td) / "old_config.json"
            cand_data = {
                "channels": {
                    "telegram": {
                        "enabled": True,
                        "bot_token": "123456:ABC-DEF",
                        "chat_id": "-100123456",
                        "proxy": "10808"
                    }
                }
            }
            cand_file.write_text(json.dumps(cand_data), encoding="utf-8")

            active_file = Path(td) / "active_config.json"
            active_data = {
                "channels": {
                    "telegram": {
                        "enabled": True,
                        "bot_token": "",
                        "chat_id": "",
                        "proxy": ""
                    }
                }
            }
            active_file.write_text(json.dumps(active_data), encoding="utf-8")

            with patch("core.config.find_active_config_file", return_value=active_file), \
                 patch("core.config.get_config_search_paths", return_value=[active_file, cand_file]), \
                 patch("core.config.save_config"):
                cfg = load_config()
                tg = cfg.get("channels", {}).get("telegram", {})
                self.assertIsInstance(tg, dict)
                self.assertEqual(tg.get("bot_token"), "123456:ABC-DEF")
                self.assertEqual(tg.get("chat_id"), "-100123456")
                self.assertEqual(tg.get("proxy"), "http://127.0.0.1:10808")

    def test_unique_active_account(self):
        mgr = AccountPoolManager()
        summary = mgr.get_accounts_summary()
        accounts = summary.get("accounts", [])
        if accounts:
            active_count = sum(1 for a in accounts if a.get("is_active"))
            self.assertLessEqual(active_count, 1, "There must be at most ONE active account in the pool")

    def test_skills_optimizer_status(self):
        from core.skills_optimizer import SkillsOptimizer
        status = SkillsOptimizer.get_status()
        self.assertIsInstance(status, dict)
        self.assertIn("available", status)
        self.assertIn("is_pruned", status)


    def test_quota_refresh_intervals(self):
        from core.config import load_config
        cfg = load_config()
        custom = cfg.get("customization", {})
        self.assertIn("quota_refresh_active_interval", custom)
        self.assertIn("quota_refresh_idle_interval", custom)
        self.assertEqual(custom["quota_refresh_active_interval"], 60)
        self.assertEqual(custom["quota_refresh_idle_interval"], 900)

    def test_multiline_and_cockpit_import_parsing(self):
        from unittest.mock import patch
        mgr = AccountPoolManager()

        # 1. 模拟多行纯文本 Token 导入
        multiline_tokens = "1//token_sample_1\n1//token_sample_2\n1//token_sample_3"
        with patch.object(AccountPoolManager, "refresh_google_token", return_value=(True, {"access_token": "ya29.test", "expires_in": 3600}, "OK")), \
             patch.object(AccountPoolManager, "fetch_user_info", return_value=(True, {"email": "mock_user@gmail.com", "name": "Mock User"}, "")), \
             patch.object(AccountPoolManager, "fetch_account_quota_data", return_value={"status": "HEALTHY", "five_hour_percent": 100}), \
             patch.object(AccountPoolManager, "save_pool"):
            ok, _, msg = mgr.add_account_by_token(multiline_tokens)
            self.assertTrue(ok)
            self.assertIn("成功批量导入", msg)

        # 2. 模拟 Cockpit Tools 导出数组格式批量导入
        cockpit_export = json.dumps([
            {"email": "cockpit1@gmail.com", "token": {"refresh_token": "1//cockpit_1"}},
            {"email": "cockpit2@gmail.com", "token": {"refresh_token": "1//cockpit_2"}}
        ])
        with patch.object(AccountPoolManager, "refresh_google_token", return_value=(True, {"access_token": "ya29.test", "expires_in": 3600}, "OK")), \
             patch.object(AccountPoolManager, "fetch_user_info", return_value=(True, {"email": "cockpit_user@gmail.com", "name": "Cockpit User"}, "")), \
             patch.object(AccountPoolManager, "fetch_account_quota_data", return_value={"status": "HEALTHY", "five_hour_percent": 100}), \
             patch.object(AccountPoolManager, "save_pool"):
            ok, _, msg = mgr.add_account_by_token(cockpit_export)
            self.assertTrue(ok)
            self.assertIn("成功批量导入 2/2", msg)

    def test_storage_manager_clean_mock(self):
        import tempfile
        from unittest.mock import patch
        from core.storage import StorageManager

        with tempfile.TemporaryDirectory() as td:
            dummy_cache = Path(td) / "Cache"
            dummy_cache.mkdir()
            (dummy_cache / "data_0.tmp").write_bytes(b"A" * 1024)

            with patch.object(StorageManager, "get_electron_user_data_dirs", return_value=[Path(td)]), \
                 patch("core.storage.BRAIN_DIR", Path(td) / "brain"), \
                 patch("core.storage.DB_PATH", Path(td) / "test.db"):
                freed, details = StorageManager.clean_storage(clean_cache=True, clean_temp_logs=False, vacuum_db=False)
                self.assertGreaterEqual(freed, 1024)
                self.assertFalse((dummy_cache / "data_0.tmp").exists())

    def test_startup_latency_benchmark(self):
        import time
        t0 = time.time()
        # 测试全栈关键模块引用与初始对象创建耗时
        import core.config
        import core.storage
        import core.account_pool
        import core.prompt_manager
        import core.localization
        import core.autostart
        import core.api_bridge
        api = core.api_bridge.OrbitApi()
        init_data = api.get_initial_data()
        elapsed = time.time() - t0
        self.assertLess(elapsed, 1.5, f"Startup elapsed time {elapsed:.3f}s exceeds benchmark of 1.5s")
        self.assertIn("config", init_data)

    def test_autostart_manager_integrity(self):
        from core.autostart import AutostartManager
        self.assertTrue(hasattr(AutostartManager, "is_enabled"))
        self.assertTrue(hasattr(AutostartManager, "enable"))
        self.assertTrue(hasattr(AutostartManager, "disable"))
        self.assertTrue(hasattr(AutostartManager, "is_app_autostart_enabled"))
        self.assertTrue(hasattr(AutostartManager, "enable_app_autostart"))
        self.assertTrue(hasattr(AutostartManager, "disable_app_autostart"))

    def test_plan_tier_and_color_thresholds_and_auto_sort(self):
        from core.account_pool import AccountPoolManager
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        import subprocess

        # 1. 验证 Python 端配额综合得分与自动排序
        with tempfile.TemporaryDirectory() as td:
            mgr = AccountPoolManager(data_dir=Path(td))
            with patch.object(mgr, "read_system_credential", return_value=(False, None, "No active credential")):
                mgr._pool_cache = {
                    "accounts": [
                        {
                            "id": "acc-low",
                            "email": "low@example.com",
                            "is_active": False,
                            "added_at": 1000,
                            "quota": {
                                "status": "LOW",
                                "tier_display": "Google AI Pro",
                                "claude_5h_percent": 30,
                                "claude_weekly_percent": 35,
                                "gemini_5h_percent": 30,
                                "gemini_weekly_percent": 35,
                            }
                        },
                        {
                            "id": "acc-full",
                            "email": "full@example.com",
                            "is_active": False,
                            "added_at": 500,
                            "quota": {
                                "status": "HEALTHY",
                                "tier_display": "Google AI Ultra",
                                "claude_5h_percent": 100,
                                "claude_weekly_percent": 100,
                                "gemini_5h_percent": 100,
                                "gemini_weekly_percent": 100,
                            }
                        },
                        {
                            "id": "acc-exhausted",
                            "email": "exhausted@example.com",
                            "is_active": False,
                            "added_at": 2000,
                            "quota": {
                                "status": "EXHAUSTED",
                                "tier_display": "Free",
                                "claude_5h_percent": 0,
                                "claude_weekly_percent": 10,
                                "gemini_5h_percent": 0,
                                "gemini_weekly_percent": 10,
                            }
                        },
                        {
                            "id": "acc-expired",
                            "email": "expired@example.com",
                            "is_active": False,
                            "added_at": 3000,
                            "quota": {
                                "status": "EXPIRED",
                                "tier_display": "Free",
                                "claude_5h_percent": 0,
                                "claude_weekly_percent": 0,
                                "gemini_5h_percent": 0,
                                "gemini_weekly_percent": 0,
                            }
                        }
                    ],
                    "active_account_id": None
                }
                summary = mgr.get_accounts_summary()
                sorted_ids = [a["id"] for a in summary["accounts"]]
                # 满额度账号 > 低额度账号 > 耗尽账号 > 失效账号
                self.assertEqual(sorted_ids, ["acc-full", "acc-low", "acc-exhausted", "acc-expired"])

                # 验证活跃（使用中）账号无论配额高低始终置顶第一位
                mgr._pool_cache["active_account_id"] = "acc-low"
                summary_active = mgr.get_accounts_summary()
                self.assertEqual(summary_active["accounts"][0]["id"], "acc-low")
                self.assertTrue(summary_active["accounts"][0]["is_active"])

        # 2. 验证前端 JS 逻辑: formatTierShort, getProgressColorClass, getAccountQuotaScore
        js_script = """
const fs = require('fs');
const vm = require('vm');
const path = require('path');
const code = fs.readFileSync(path.join(__dirname, 'core', 'web', 'app.js'), 'utf-8');

const context = {
  console: console,
  document: {
    getElementById: () => ({ textContent: '', innerHTML: '', className: '', style: {} }),
    querySelector: () => ({ textContent: '', innerHTML: '', className: '', style: {} }),
    querySelectorAll: () => [],
    addEventListener: () => {}
  },
  window: {},
  appState: { config: {}, status: {}, account_pool: { accounts: [] } },
  setInterval: () => {},
  clearInterval: () => {},
  clearTimeout: () => {},
  Math: Math,
  Date: Date,
  JSON: JSON,
  parseInt: parseInt,
  parseFloat: parseFloat,
  encodeURIComponent: encodeURIComponent,
  decodeURIComponent: decodeURIComponent
};
context.window = context;
context.addEventListener = () => {};
vm.createContext(context);
vm.runInContext(code, context);

// 1. 验证 formatTierShort
if (context.formatTierShort('Google AI Pro') !== 'Pro') throw new Error('formatTierShort failed on Google AI Pro');
if (context.formatTierShort('GOOGLE AI PRO') !== 'Pro') throw new Error('formatTierShort failed on GOOGLE AI PRO');
if (context.formatTierShort('Google AI Ultra') !== 'Ultra') throw new Error('formatTierShort failed on Google AI Ultra');
if (context.formatTierShort('免费版') !== 'Free') throw new Error('formatTierShort failed on 免费版');
if (context.formatTierShort('Free') !== 'Free') throw new Error('formatTierShort failed on Free');

// 2. 验证 getProgressColorClass 阈值 (<15% 红色, <40% 黄色, >=40% 绿色)
if (context.getProgressColorClass(0) !== 'fill-exhausted') throw new Error('0% should be fill-exhausted');
if (context.getProgressColorClass(14.9) !== 'fill-exhausted') throw new Error('14.9% should be fill-exhausted');
if (context.getProgressColorClass(15) !== 'fill-warning') throw new Error('15% should be fill-warning');
if (context.getProgressColorClass(39.9) !== 'fill-warning') throw new Error('39.9% should be fill-warning');
if (context.getProgressColorClass(40) !== 'fill-healthy') throw new Error('40% should be fill-healthy');
if (context.getProgressColorClass(100) !== 'fill-healthy') throw new Error('100% should be fill-healthy');

// 3. 验证自动排序打分
const sFull = context.getAccountQuotaScore({ quota: { claude_5h_percent: 100, claude_weekly_percent: 100, gemini_5h_percent: 100, gemini_weekly_percent: 100 } });
const sMid = context.getAccountQuotaScore({ quota: { claude_5h_percent: 50, claude_weekly_percent: 50, gemini_5h_percent: 50, gemini_weekly_percent: 50 } });
const sZero = context.getAccountQuotaScore({ quota: { status: 'EXHAUSTED', claude_5h_percent: 0, claude_weekly_percent: 0, gemini_5h_percent: 0, gemini_weekly_percent: 0 } });
const sExp = context.getAccountQuotaScore({ quota: { status: 'EXPIRED' } });

if (!(sFull > sMid && sMid > sZero && sZero > sExp)) {
  throw new Error(`getAccountQuotaScore order failed: full=${sFull}, mid=${sMid}, zero=${sZero}, exp=${sExp}`);
}

// 4. 验证活跃账号在前端始终置顶第 1 位
const testAccs = [
  { id: 'acc1', is_active: false, quota: { claude_5h_percent: 100, claude_weekly_percent: 100, gemini_5h_percent: 100, gemini_weekly_percent: 100 } },
  { id: 'acc2', is_active: true, quota: { claude_5h_percent: 10, claude_weekly_percent: 10, gemini_5h_percent: 10, gemini_weekly_percent: 10 } }
];
testAccs.sort((a, b) => {
  if (a.is_active && !b.is_active) return -1;
  if (!a.is_active && b.is_active) return 1;
  return context.getAccountQuotaScore(b) - context.getAccountQuotaScore(a);
});
if (testAccs[0].id !== 'acc2') throw new Error('Active account must be pinned at index 0');

// 5. 验证诊断模态框控制器函数注册完整
if (typeof context.showAccountStatusModal !== 'function') throw new Error('showAccountStatusModal missing');
if (typeof context.handleCloseAccountStatusModal !== 'function') throw new Error('handleCloseAccountStatusModal missing');

console.log('ALL_OK');
"""
        res = subprocess.run(["node", "-e", js_script], capture_output=True, text=True, cwd=str(Path(__file__).parent.parent))
        self.assertEqual(res.returncode, 0, f"JS verification failed: {res.stderr}")
        self.assertIn("ALL_OK", res.stdout)

    def test_focus_and_launch_antigravity(self):
        from core.localization import LocalizationManager
        self.assertTrue(hasattr(LocalizationManager, "focus_antigravity"))
        self.assertTrue(hasattr(LocalizationManager, "launch_antigravity"))

    def test_tray_menu_and_window_state(self):
        """测试托盘右键菜单纯净无图标、动态文案切换及全屏最大化唤醒状态"""
        from unittest.mock import patch, MagicMock
        from core.gui import OrbitWindowManager
        from core.localization import LocalizationManager
        from core.autostart import AutostartManager

        mgr = OrbitWindowManager(start_in_tray=True)
        self.assertTrue(mgr.start_in_tray)

        # 1. 验证动态文案：反重力未运行时为「开启反重力」，运行时为「重启反重力」
        with patch.object(LocalizationManager, "is_running", return_value=False):
            title_stopped = mgr._get_antigravity_menu_text()
            self.assertEqual(title_stopped, "开启反重力")

        with patch.object(LocalizationManager, "is_running", return_value=True):
            title_running = mgr._get_antigravity_menu_text()
            self.assertEqual(title_running, "重启反重力")

        # 2. 验证文案中绝无任何 emoji 或乱码图标
        for text in [title_stopped, title_running, "打开管理中心", "退出"]:
            self.assertTrue(all(ord(c) < 0x10000 and c not in ["🖥️", "🚀", "🚪", "✨", "🔄"] for c in text))

        # 3. 验证 show_window 将 start_in_tray 重置为 False
        fake_window = MagicMock()
        mgr.window = fake_window
        with patch("threading.Timer"):
            mgr.show_window()
        self.assertFalse(mgr.start_in_tray)
        fake_window.show.assert_called_once()
        fake_window.maximize.assert_called_once()

        # 4. 验证 AutostartManager 路径检索
        self.assertTrue(hasattr(AutostartManager, "_find_installed_app_exe"))

    def test_default_fresh_install_switches_all_disabled(self):
        """测试新用户初次安装时所有功能开关默认关闭，绝不擅自开启"""
        from core.config import DEFAULT_CONFIG
        import json
        from pathlib import Path

        custom = DEFAULT_CONFIG.get("customization", {})
        switches = [
            "enable_gpu_acceleration",
            "disable_background_throttling",
            "expand_v8_memory",
            "disable_telemetry",
            "hide_ide_buttons",
            "clean_ui",
            "opt_gpu",
            "opt_max_heap",
            "opt_nosleep",
            "opt_telemetry",
            "show_quota_badge",
            "proxy_enabled",
            "start_maximized",
            "auto_retry_on_error",
            "notify_on_quota_exhausted",
        ]
        for sw in switches:
            self.assertFalse(custom.get(sw, False), f"Default customization switch '{sw}' should be False!")

        # 说明型 Skills 裁剪默认开启并持久记忆 (节省前置 Token 预算，杜绝重新安装后被自动关闭)
        self.assertTrue(custom.get("prune_guide_skills", True))

        self.assertFalse(DEFAULT_CONFIG.get("close_to_tray", False))
        self.assertFalse(DEFAULT_CONFIG.get("app_autostart", False))
        self.assertFalse(DEFAULT_CONFIG.get("channels", {}).get("telegram", {}).get("enabled", False))

        # 验证 config.example.json 中除 prune_guide_skills 之外开关也是默认关闭
        example_path = Path(__file__).parent.parent / "config.example.json"
        self.assertTrue(example_path.exists())
        example_cfg = json.loads(example_path.read_text(encoding="utf-8"))
        ex_custom = example_cfg.get("customization", {})
        for sw in switches:
            self.assertFalse(ex_custom.get(sw, False), f"config.example.json switch '{sw}' should be False!")
        self.assertTrue(ex_custom.get("prune_guide_skills", True))
        self.assertFalse(example_cfg.get("close_to_tray", False))
        self.assertFalse(example_cfg.get("app_autostart", False))

    def test_config_corruption_recovery_and_deepcopy_integrity(self):
        """测试配置损坏时自动降级与全局 DEFAULT_CONFIG 免疫被污染深拷贝特性"""
        import tempfile
        from unittest.mock import patch
        from core.config import load_config, DEFAULT_CONFIG

        with tempfile.TemporaryDirectory() as temp_dir:
            corrupt_cfg = Path(temp_dir) / "config.json"
            # 测试 1: 非法 JSON 字符串
            corrupt_cfg.write_text("{broken json", encoding="utf-8")
            with patch("core.config.find_active_config_file", return_value=corrupt_cfg):
                cfg = load_config()
                self.assertIsInstance(cfg, dict)
                self.assertIn("customization", cfg)
                # 尝试修改返回对象
                cfg["customization"]["test_dirty"] = True
                self.assertNotIn("test_dirty", DEFAULT_CONFIG["customization"], "DEFAULT_CONFIG must not be polluted!")

            # 测试 2: JSON 顶层为数组而非字典
            corrupt_cfg.write_text("[1, 2, 3]", encoding="utf-8")
            with patch("core.config.find_active_config_file", return_value=corrupt_cfg):
                cfg2 = load_config()
                self.assertIsInstance(cfg2, dict)
                self.assertIn("customization", cfg2)

    def test_monitor_lifecycle_and_lock_cleanup(self):
        """测试监控引擎守护与锁释放安全，绝不触发 NameError"""
        from core.monitor import AntigravityMonitor
        monitor = AntigravityMonitor()
        self.assertTrue(monitor._running)
        # 验证优雅退出
        monitor.stop()
        self.assertFalse(monitor._running)

    def test_api_bridge_open_config_dir_cross_platform(self):
        """测试各操作系统下打开配置目录行为"""
        from unittest.mock import patch
        api = OrbitApi()

        with patch("platform.system", return_value="Windows"), \
             patch("os.startfile") as mock_startfile:
            res = api.open_config_dir()
            self.assertTrue(res["success"])
            mock_startfile.assert_called_once()

        with patch("platform.system", return_value="Darwin"), \
             patch("subprocess.Popen") as mock_popen:
            res = api.open_config_dir()
            self.assertTrue(res["success"])
            mock_popen.assert_called_once()
            args = mock_popen.call_args[0][0]
            self.assertEqual(args[0], "open")

        with patch("platform.system", return_value="Linux"), \
             patch("subprocess.Popen") as mock_popen:
            res = api.open_config_dir()
            self.assertTrue(res["success"])
            mock_popen.assert_called_once()
            args = mock_popen.call_args[0][0]
            self.assertEqual(args[0], "xdg-open")

    def test_account_pool_find_best_healthy_account(self):
        """测试从账号池中智能挑选额度最健康充足的备用账号算法"""
        import tempfile
        from unittest.mock import patch
        from core.account_pool import AccountPoolManager

        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = AccountPoolManager(data_dir=Path(tmpdir))
            mgr._pool_cache = {
                "active_account_id": "acc-1",
                "accounts": [
                    {
                        "id": "acc-1",
                        "email": "low@test.com",
                        "status": "WARNING",
                        "token": {"refresh_token": "rf_1"},
                        "quota": {"gemini_5h_fraction": 0.05, "gemini_weekly_fraction": 0.2}
                    },
                    {
                        "id": "acc-2",
                        "email": "exhausted@test.com",
                        "status": "EXHAUSTED",
                        "token": {"refresh_token": "rf_2"},
                        "quota": {"gemini_5h_fraction": 0.0, "gemini_weekly_fraction": 0.0}
                    },
                    {
                        "id": "acc-3",
                        "email": "best@test.com",
                        "status": "HEALTHY",
                        "token": {"refresh_token": "rf_3"},
                        "quota": {"gemini_5h_fraction": 0.95, "gemini_weekly_fraction": 0.9}
                    },
                    {
                        "id": "acc-4",
                        "email": "mid@test.com",
                        "status": "HEALTHY",
                        "token": {"refresh_token": "rf_4"},
                        "quota": {"gemini_5h_fraction": 0.60, "gemini_weekly_fraction": 0.8}
                    }
                ]
            }
            mgr.save_pool()

            best = mgr.find_best_healthy_account(exclude_account_id="acc-1")
            self.assertIsNotNone(best)
            self.assertEqual(best["email"], "best@test.com")
            self.assertEqual(best["id"], "acc-3")

            # 排除 acc-3 后，次优为 acc-4
            second = mgr.find_best_healthy_account(exclude_account_id="acc-3")
            self.assertEqual(second["email"], "mid@test.com")

    def test_account_pool_auto_switch_on_low_quota(self):
        """测试低额度自动无感热切换逻辑 (触发、跳过与强制切号)"""
        import tempfile
        from unittest.mock import patch
        from core.account_pool import AccountPoolManager

        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = AccountPoolManager(data_dir=Path(tmpdir))
            mgr._pool_cache = {
                "active_account_id": "acc-1",
                "accounts": [
                    {
                        "id": "acc-1",
                        "email": "current_low@test.com",
                        "status": "WARNING",
                        "token": {"refresh_token": "rf_1", "access_token": "acc_1"},
                        "quota": {"gemini_5h_fraction": 0.08, "gemini_weekly_fraction": 0.5}
                    },
                    {
                        "id": "acc-2",
                        "email": "healthy_next@test.com",
                        "status": "HEALTHY",
                        "token": {"refresh_token": "rf_2", "access_token": "acc_2"},
                        "quota": {"gemini_5h_fraction": 0.85, "gemini_weekly_fraction": 0.9}
                    }
                ]
            }
            mgr.save_pool()

            with patch.object(mgr, "write_system_credential", return_value=(True, "OK")), \
                 patch.object(mgr, "refresh_google_token", return_value=(True, {"access_token": "new_tok"}, "")), \
                 patch("core.localization.LocalizationManager.is_running", return_value=False):

                # 1. 阈值 10%：当前 8% <= 10%，应成功切号
                ok, target, msg = mgr.auto_switch_on_low_quota(threshold_pct=10.0)
                self.assertTrue(ok)
                self.assertEqual(target["email"], "healthy_next@test.com")
                self.assertEqual(mgr._pool_cache["active_account_id"], "acc-2")

                # 2. 当前已是 85%，再次执行不应触发切号
                ok_skip, _, msg_skip = mgr.auto_switch_on_low_quota(threshold_pct=10.0)
                self.assertFalse(ok_skip)
                self.assertIn("额度充足", msg_skip)

                # 3. 强制切号 force=True：即使额度充足也会切回最优可用备用号
                ok_force, target_force, _ = mgr.auto_switch_on_low_quota(threshold_pct=10.0, force=True)
                self.assertTrue(ok_force)
                self.assertEqual(target_force["email"], "current_low@test.com")

    def test_api_bridge_auto_switch_config_and_actions(self):
        """测试 ApiBridge 低额度自动热切换接口与默认免重启配置"""
        from unittest.mock import patch
        api = OrbitApi()

        # 1. switch_account 默认免重启 (restart_app=False)
        with patch.object(api._account_mgr, "switch_account", return_value=(True, "已成功切换账号（已完成免重启热切换）")), \
             patch("core.localization.LocalizationManager.kill_running_antigravity") as mock_kill:
            res = api.switch_account("some_id", restart_app=False)
            self.assertTrue(res["success"])
            self.assertIn("免重启", res["message"])
            mock_kill.assert_not_called()

        # 2. 读写自动热切换配置
        with patch("core.api_bridge.load_config", return_value={"customization": {"auto_switch_on_low_quota": False, "low_quota_threshold_pct": 10}}), \
             patch("core.api_bridge.save_config") as mock_save:
            cfg_res = api.get_auto_switch_config()
            self.assertTrue(cfg_res["success"])
            self.assertFalse(cfg_res["enabled"])
            self.assertEqual(cfg_res["threshold"], 10)

            set_res = api.set_auto_switch_config(True, 15)
            self.assertTrue(set_res["success"])
            mock_save.assert_called_once()
            saved_cfg = mock_save.call_args[0][0]
            self.assertTrue(saved_cfg["customization"]["auto_switch_on_low_quota"])
            self.assertEqual(saved_cfg["customization"]["low_quota_threshold_pct"], 15)

    def test_monitor_dispatch_notification_auto_switch(self):
        """测试监控引擎在捕获额度耗尽通知时自动无感切号接力"""
        from unittest.mock import patch, MagicMock
        from core.monitor import AntigravityMonitor

        mon = AntigravityMonitor()
        mon.config = {
            "enabled": True,
            "customization": {
                "auto_switch_on_low_quota": True,
                "auto_switch_cooldown_sec": 60
            }
        }

        mock_mgr = MagicMock()
        mock_mgr.auto_switch_on_low_quota.return_value = (True, {"email": "switched@test.com"}, "OK")

        with patch("core.monitor.load_config", return_value=mon.config), \
             patch("core.monitor.get_active_notifiers", return_value=[]), \
             patch("core.account_pool.AccountPoolManager", return_value=mock_mgr):

            # 触发额度耗尽通知
            mon.dispatch_notification("TestProject", "任务中断：额度已耗尽", "429 Rate limit exceeded")
            mock_mgr.auto_switch_on_low_quota.assert_called_once_with(force=True)

    def test_localization_is_any_task_running(self):
        """测试 LocalizationManager 探测长任务运行状态"""
        from unittest.mock import patch, MagicMock
        from core.localization import LocalizationManager
        from pathlib import Path

        # 1. 数据库不存在时返回 False
        with patch("core.config.DB_PATH", Path("non_existent_db.sqlite")):
            self.assertFalse(LocalizationManager.is_any_task_running())

        # 2. 模拟数据库返回有长任务在跑 (RUNNING / not_fully_idle=1)
        mock_con = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = (1,)
        mock_con.cursor.return_value = mock_cur

        with patch("core.config.DB_PATH", Path(__file__)), \
             patch("sqlite3.connect", return_value=mock_con):
            self.assertTrue(LocalizationManager.is_any_task_running())

        # 3. 模拟数据库返回空闲 (无正在运行的会话)
        mock_cur.fetchone.return_value = None
        with patch("core.config.DB_PATH", Path(__file__)), \
             patch("sqlite3.connect", return_value=mock_con):
            self.assertFalse(LocalizationManager.is_any_task_running())

    def test_switch_account_zero_interruption_protection(self):
        """测试 switch_account 在长任务运行中启用零中断保护（不杀进程，延时接力）"""
        import tempfile
        from unittest.mock import patch
        from core.account_pool import AccountPoolManager

        with tempfile.TemporaryDirectory() as td:
            mgr = AccountPoolManager(data_dir=Path(td))
            mgr._pool_cache = {
                "active_account_id": "acc-1",
                "accounts": [
                    {
                        "id": "acc-1",
                        "email": "task_running@test.com",
                        "token": {"access_token": "tok1", "refresh_token": "rf1"}
                    },
                    {
                        "id": "acc-2",
                        "email": "healthy_next@test.com",
                        "token": {"access_token": "tok2", "refresh_token": "rf2"}
                    }
                ]
            }

            with patch.object(mgr, "write_system_credential", return_value=(True, "OK")), \
                 patch.object(mgr, "refresh_google_token", return_value=(True, {"access_token": "new_tok"}, "")), \
                 patch("core.localization.LocalizationManager.is_running", return_value=True), \
                 patch("core.localization.LocalizationManager.is_any_task_running", return_value=True), \
                 patch("core.localization.LocalizationManager.reload_language_server", return_value=(True, "OK")) as mock_reload:

                # 1. 切换账号：长任务正在运行中，必须严禁调用 reload_language_server
                ok, msg = mgr.switch_account("acc-2", reload_session=True, force_reload=False)
                self.assertTrue(ok)
                self.assertIn("零中断保护", msg)
                self.assertTrue(mgr.has_pending_reload())
                mock_reload.assert_not_called()

                # 2. force_reload=True 强制重载模式下，应直接触发重载
                ok_force, msg_force = mgr.switch_account("acc-2", reload_session=True, force_reload=True)
                self.assertTrue(ok_force)
                self.assertIn("已无感热重载生效", msg_force)
                mock_reload.assert_called_once()
                self.assertFalse(mgr.has_pending_reload())

    def test_pending_reload_auto_execution_on_idle(self):
        """测试长任务由 RUNNING 恢复为空闲 IDLE 时，自动触发平滑重载接力"""
        from unittest.mock import patch, MagicMock
        from core.account_pool import AccountPoolManager
        from core.localization import LocalizationManager

        AccountPoolManager.set_pending_reload(True, email="pending@test.com")
        self.assertTrue(AccountPoolManager.has_pending_reload())

        with patch.object(LocalizationManager, "reload_language_server", return_value=(True, "OK")) as mock_reload:
            # 模拟执行检查：任务已处于空闲
            with patch.object(LocalizationManager, "is_any_task_running", return_value=False):
                if AccountPoolManager.has_pending_reload() and not LocalizationManager.is_any_task_running():
                    mock_reload()
                    AccountPoolManager.set_pending_reload(False)

            self.assertFalse(AccountPoolManager.has_pending_reload())
            mock_reload.assert_called_once()

    def test_monitor_periodic_quota_polling(self):
        """测试监控引擎定期巡检活跃账号额度并在低于阈值时触发自动热切换"""
        from unittest.mock import patch, MagicMock
        from core.monitor import AntigravityMonitor

        mon = AntigravityMonitor()
        mon.config = {
            "enabled": True,
            "customization": {
                "auto_switch_on_low_quota": True,
                "low_quota_threshold_pct": 10,
                "auto_switch_cooldown_sec": 60
            }
        }

        mock_mgr = MagicMock()
        mock_mgr.get_active_account_id.return_value = "acc-low"
        mock_mgr.refresh_single_account_quota.return_value = (True, {"gemini_5h_fraction": 0.08}, "OK")
        mock_mgr.auto_switch_on_low_quota.return_value = (True, {"email": "switched@test.com"}, "OK")

        # 模拟执行周期逻辑
        now_ts = 1000.0
        custom = mon.config["customization"]
        thresh = float(custom.get("low_quota_threshold_pct", 10))
        ref_ok, quota_data, _ = mock_mgr.refresh_single_account_quota("acc-low")
        self.assertTrue(ref_ok)
        g_5h = quota_data.get("gemini_5h_fraction")
        self.assertLessEqual(g_5h * 100.0, thresh)
        sw_ok, new_acc, _ = mock_mgr.auto_switch_on_low_quota(threshold_pct=thresh)
        self.assertTrue(sw_ok)
        self.assertEqual(new_acc["email"], "switched@test.com")

    def test_quota_calculation_accuracy(self):
        """测试多版本配额格式的精准解析与归一化百分比计算"""
        from core.account_pool import AccountPoolManager

        # 1. 常见完整格式：含有 five_hour_percent 与 gemini_5h_percent
        acc1 = {"quota": {"five_hour_percent": 85, "five_hour_fraction": 0.85}}
        self.assertEqual(AccountPoolManager.get_account_quota_pct(acc1), 85.0)

        # 2. 只有 gemini_5h_percent
        acc2 = {"quota": {"gemini_5h_percent": 42}}
        self.assertEqual(AccountPoolManager.get_account_quota_pct(acc2), 42.0)

        # 3. 只有小数形式 five_hour_fraction (例如 0.08)
        acc3 = {"quota": {"five_hour_fraction": 0.08}}
        self.assertAlmostEqual(AccountPoolManager.get_account_quota_pct(acc3), 8.0, places=1)

        # 4. 状态异常 (EXHAUSTED / EXPIRED)
        acc4 = {"quota": {"status": "EXHAUSTED"}}
        self.assertEqual(AccountPoolManager.get_account_quota_pct(acc4), 0.0)

        # 5. 空配额默认值
        self.assertEqual(AccountPoolManager.get_account_quota_pct({}), 0.0)
        self.assertEqual(AccountPoolManager.get_account_quota_pct({"quota": {}}), 100.0)

    def test_reload_language_server_safety_lock(self):
        """测试 reload_language_server 内置零中断安全锁：只要任务在跑，严格拒绝杀进程"""
        from unittest.mock import patch
        from core.localization import LocalizationManager

        with patch.object(LocalizationManager, "is_any_task_running", return_value=True), \
             patch.object(LocalizationManager, "_run_subp") as mock_subp:

            # 未指定 force 时，探测到有任务在跑，必须直接拦截并返回 False
            ok, msg = LocalizationManager.reload_language_server(force=False)
            self.assertFalse(ok)
            self.assertIn("零中断保护", msg)
            mock_subp.assert_not_called()

    def test_auto_switch_on_low_quota_protects_short_and_long_tasks(self):
        """测试额度低于阈值时，自动热切号在短任务与长任务执行中均能完整保护不中断"""
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from core.account_pool import AccountPoolManager
        from core.localization import LocalizationManager

        with tempfile.TemporaryDirectory() as td:
            mgr = AccountPoolManager(data_dir=Path(td))
            mgr._pool_cache = {
                "active_account_id": "acc-low",
                "accounts": [
                    {
                        "id": "acc-low",
                        "email": "low_quota@test.com",
                        "token": {"access_token": "tok1", "refresh_token": "rf1"},
                        "quota": {"five_hour_percent": 8}  # 8% <= 10%
                    },
                    {
                        "id": "acc-high",
                        "email": "high_quota@test.com",
                        "token": {"access_token": "tok2", "refresh_token": "rf2"},
                        "quota": {"five_hour_percent": 95}
                    }
                ]
            }

            with patch.object(mgr, "write_system_credential", return_value=(True, "OK")), \
                 patch.object(mgr, "refresh_google_token", return_value=(True, {"access_token": "new"}, "")), \
                 patch.object(LocalizationManager, "is_running", return_value=True), \
                 patch.object(LocalizationManager, "is_any_task_running", return_value=True), \
                 patch.object(LocalizationManager, "reload_language_server") as mock_reload:

                # 模拟任务（不管是 2 秒的短任务，还是 5 分钟的长任务）正在跑
                ok, target, msg = mgr.auto_switch_on_low_quota(threshold_pct=10.0)

                # 1. 切号必须成功记录
                self.assertTrue(ok)
                self.assertEqual(target["email"], "high_quota@test.com")
                self.assertEqual(mgr._pool_cache["active_account_id"], "acc-high")

                # 2. 绝不杀进程，长/短任务零中断保护生效
                mock_reload.assert_not_called()
                self.assertTrue(mgr.has_pending_reload())
                self.assertIn("零中断保护", msg)

    def test_clean_sidebar_and_menu_config_and_version(self):
        """测试 v3.3.16 版本号与极简侧栏顶栏配置项定义"""
        from core.config import APP_VERSION, DEFAULT_CONFIG
        self.assertEqual(APP_VERSION, "3.3.16")
        self.assertIn("clean_sidebar_and_menu", DEFAULT_CONFIG["customization"])

    def test_runtime_translation_isolation_and_clean_sidebar(self):
        """测试汉化引擎对代码/命令字词（如 apt update && apt install）的隔离保护与极简侧栏注入"""
        import subprocess
        node_script = """
        const { LocalizationEngine } = require('./localization/core/engine');
        const engine = new LocalizationEngine();
        const runtime = engine.generateRuntimeScript(false, { clean_sidebar_and_menu: true });
        
        if (!runtime.includes('ISOLATED_UI_WORDS')) throw new Error('ISOLATED_UI_WORDS missing');
        if (!runtime.includes('injectCleanSidebarStyle')) throw new Error('injectCleanSidebarStyle missing');
        if (!runtime.includes('mountTopSettingsButton')) throw new Error('mountTopSettingsButton missing');
        if (!runtime.includes('clean_sidebar_and_menu')) throw new Error('clean_sidebar_and_menu missing');
        
        // 验证关键词清单
        const words = ['update', 'install', 'run', 'build'];
        for (const w of words) {
            if (!runtime.includes(`'${w}'`)) throw new Error(`Keyword ${w} missing from isolation list`);
        }
        process.exit(0);
        """
        res = subprocess.run(["node", "-e", node_script], cwd=Path(__file__).parent.parent, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Node verification failed: {res.stderr}")

if __name__ == "__main__":
    unittest.main()





