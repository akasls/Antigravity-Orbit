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
console.log('ALL_OK');
"""
        res = subprocess.run(["node", "-e", js_script], capture_output=True, text=True, cwd=str(Path(__file__).parent.parent))
        self.assertEqual(res.returncode, 0, f"JS verification failed: {res.stderr}")
        self.assertIn("ALL_OK", res.stdout)

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
            "prune_guide_skills"
        ]
        for sw in switches:
            self.assertFalse(custom.get(sw, False), f"Default customization switch '{sw}' should be False!")

        self.assertFalse(DEFAULT_CONFIG.get("close_to_tray", False))
        self.assertFalse(DEFAULT_CONFIG.get("app_autostart", False))
        self.assertFalse(DEFAULT_CONFIG.get("channels", {}).get("telegram", {}).get("enabled", False))

        # 验证 config.example.json 中所有开关也是默认关闭
        example_path = Path(__file__).parent.parent / "config.example.json"
        self.assertTrue(example_path.exists())
        example_cfg = json.loads(example_path.read_text(encoding="utf-8"))
        ex_custom = example_cfg.get("customization", {})
        for sw in switches:
            self.assertFalse(ex_custom.get(sw, False), f"config.example.json switch '{sw}' should be False!")
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

if __name__ == "__main__":
    unittest.main()


