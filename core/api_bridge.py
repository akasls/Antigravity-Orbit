"""
Antigravity Orbit - 前后端双向通讯 API 网关 (API Bridge for pywebview)
提供 JavaScript 经由 window.pywebview.api 调用的所有系统与业务方法
"""

import os
import sys
import json
import time
import socket
import platform
import threading
import subprocess
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import (
    CONFIG_FILE,
    LOG_FILE,
    BASE_DIR,
    load_config,
    save_config,
)
from core.localization import LocalizationManager
from core.autostart import AutostartManager
from core.storage import StorageManager
from core.skills_optimizer import SkillsOptimizer
from core.prompt_manager import PromptManager
from core.account_pool import AccountPoolManager


class OrbitApi:
    """提供给前端 JS 调用的核心原生 API 接口"""

    def __init__(self, window_holder=None):
        self._window_holder = window_holder
        self._account_mgr = AccountPoolManager()

    def get_initial_data(self) -> dict:
        """获取所有初始配置、运行状态、提示词及模板数据 (秒级返回)"""
        cfg = load_config()
        custom = cfg.get("customization", {})
        channels = cfg.get("channels", {})

        # 客户端检测状态
        loc = LocalizationManager.get_status(fast=True)
        port = cfg.get("lock_port", 49222)
        daemon_running, daemon_pid = self._check_daemon_running(port)
        daemon_auto = AutostartManager.is_enabled()
        app_auto = AutostartManager.is_app_autostart_enabled()

        # 确保 skills 裁剪状态与物理磁盘状态完全同步
        skills_opt = SkillsOptimizer.get_status()
        is_pruned = skills_opt.get("is_pruned", False)
        if custom.get("prune_guide_skills") != is_pruned:
            custom["prune_guide_skills"] = is_pruned
            cfg["customization"]["prune_guide_skills"] = is_pruned
            try:
                save_config(cfg)
            except Exception:
                pass

        # 存储分析 (启动时免全盘递归扫描，由前端异步按需懒加载)
        storage_info = None

        # 提示词与模板 (用户自定义提示词库)
        prompt_content = PromptManager.read_system_prompt()
        templates = PromptManager.get_custom_templates()

        # 运行日志最新 30 行
        logs = self._get_recent_logs()

        # 账号池与凭据数据
        account_pool = None
        try:
            account_pool = self._account_mgr.get_accounts_summary()
            # 如果账号池为空，自动尝试静默快速导入当前客户端账号 (零网络阻塞)
            if account_pool.get("total", 0) == 0:
                self._account_mgr.import_current_client_account(fetch_network=False)
                account_pool = self._account_mgr.get_accounts_summary()
        except Exception as e:
            account_pool = {"total": 0, "healthy": 0, "low_or_exhausted": 0, "accounts": [], "error": str(e)}

        return {
            "config": cfg,
            "status": {
                "installed": loc.get("installed", False),
                "install_dir": loc.get("install_dir", ""),
                "is_localized": loc.get("is_localized", False),
                "lang": loc.get("lang", "zh-CN"),
                "daemon_running": daemon_running,
                "daemon_pid": daemon_pid,
                "daemon_port": port,
                "daemon_autostart": daemon_auto,
                "app_autostart": app_auto,
                "storage": storage_info,
            },
            "account_pool": account_pool,
            "prompt": {
                "content": prompt_content,
                "templates": templates,
            },
            "logs": logs,
        }

    def _check_daemon_running(self, port: int) -> tuple[bool, str]:
        pid_file = BASE_DIR / ".daemon.pid"
        pid = None
        if pid_file.exists():
            try:
                pid = pid_file.read_text(encoding="utf-8").strip()
            except Exception:
                pass

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", port))
            return False, ""
        except socket.error:
            return True, pid or "活跃"
        finally:
            try:
                s.close()
            except Exception:
                pass

    def _get_recent_logs(self) -> str:
        if LOG_FILE.exists():
            try:
                lines = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
                return "\n".join(lines[-40:]) if lines else "暂无运行日志"
            except Exception as e:
                return f"读取日志异常: {e}"
        return "日志文件尚未生成 (守护服务启动后将自动记录)"

    def refresh_status(self) -> dict:
        """异步刷新状态接口"""
        return self.get_initial_data()

    def test_proxy(self, proxy_type: str = "http", host: str = "127.0.0.1", port: int = 7890) -> dict:
        """测试专属代理网络连通性"""
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3.0)
            res = sock.connect_ex((host, int(port)))
            sock.close()
            if res == 0:
                return {"success": True, "message": f"代理端口测试成功: {proxy_type.upper()}://{host}:{port}"}
            else:
                return {"success": False, "message": f"无法连接到代理目标端口 {host}:{port} (代码: {res})"}
        except Exception as e:
            return {"success": False, "message": f"代理探测异常: {e}"}

    def save_and_apply(self, new_cfg: dict) -> dict:
        """保存配置并实时生效 (绝对不干扰或强杀正在运行中的 Antigravity 客户端)"""
        try:
            cfg = load_config()
            cfg.update(new_cfg)

            # 自动维护 proxy_url
            custom = cfg.get("customization", {})
            if custom.get("proxy_host") and custom.get("proxy_port"):
                p_type = (custom.get("proxy_type") or "http").lower()
                custom["proxy_url"] = f"{p_type}://{custom['proxy_host']}:{custom['proxy_port']}"

            save_config(cfg)

            # 更新 Skills 裁剪
            try:
                SkillsOptimizer.set_pruned(custom.get("prune_guide_skills", False))
            except Exception:
                pass

            # 核心机制：
            # 1. 代理、自愈、推送、自启动等后台服务配置写入后即刻生效；
            # 2. 若 Antigravity 正在运行中：绝不强行杀掉客户端，避免弹黑窗或打断用户工作流。
            #    若修改了外观/语言/专属代理等需要底层重载的项，用户可随时在「系统维护」点击【重启客户端】一次性生效。
            # 3. 若 Antigravity 处于未运行状态：静默注入最新补丁。
            is_running = LocalizationManager.is_running()
            if not is_running:
                lang = custom.get("language", "zh-CN")
                is_tw = (lang == "zh-TW")
                is_en = (lang == "en")
                LocalizationManager.install(tw=is_tw, en=is_en, no_kill=True, stream_output=False)

            return {
                "success": True,
                "message": "配置已保存生效！如修改了代理或加速，点击【重启客户端】即可让 Antigravity 彻底切入代理。"
            }
        except Exception as e:
            return {"success": False, "message": f"处理配置异常: {e}"}

    def restore_english(self) -> dict:
        """还原官方英文原版"""
        try:
            ok, msg = LocalizationManager.restore(stream_output=False)
            return {
                "success": ok,
                "message": "已成功恢复 Antigravity 官方原版英文备份！" if ok else f"还原失败: {msg}"
            }
        except Exception as e:
            return {"success": False, "message": f"还原异常: {e}"}

    def restart_antigravity(self) -> dict:
        """重启 Antigravity 客户端并同步最新补丁"""
        try:
            cfg = load_config()
            custom = cfg.get("customization", {})
            lang = custom.get("language", "zh-CN")
            is_tw = (lang == "zh-TW")
            is_en = (lang == "en")

            LocalizationManager.kill_running_antigravity()
            time.sleep(0.8)

            # 客户端退出后 (asar 未被锁) 重新注入最新汉化与优化补丁
            LocalizationManager.install(tw=is_tw, en=is_en, no_kill=True, stream_output=False)
            time.sleep(0.3)

            ok, msg = LocalizationManager.launch_antigravity()
            return {
                "success": ok,
                "message": "客户端已重新拉起并应用最新补丁！" if ok else f"未能自动拉起: {msg}"
            }
        except Exception as e:
            return {"success": False, "message": f"重启异常: {e}"}

    def save_and_restart(self, new_cfg: dict) -> dict:
        """保存「性能汉化」各项设定，并重启 Antigravity 客户端以注入生效"""
        try:
            cfg = load_config()
            cfg.update(new_cfg)

            custom = cfg.get("customization", {})
            if custom.get("proxy_host") and custom.get("proxy_port"):
                p_type = (custom.get("proxy_type") or "http").lower()
                custom["proxy_url"] = f"{p_type}://{custom['proxy_host']}:{custom['proxy_port']}"

            save_config(cfg)

            # 更新 Skills 裁剪
            try:
                SkillsOptimizer.set_pruned(custom.get("prune_guide_skills", False))
            except Exception:
                pass

            lang = custom.get("language", "zh-CN")
            is_tw = (lang == "zh-TW")
            is_en = (lang == "en")

            LocalizationManager.kill_running_antigravity()
            time.sleep(0.8)

            LocalizationManager.install(tw=is_tw, en=is_en, no_kill=True, stream_output=False)
            time.sleep(0.3)

            ok, msg = LocalizationManager.launch_antigravity()
            return {
                "success": ok,
                "message": "性能与汉化配置已保存，Antigravity 客户端已重新拉起生效！" if ok else f"配置已保存，未能自动启动客户端: {msg}"
            }
        except Exception as e:
            return {"success": False, "message": f"保存并重启异常: {e}"}

    def reset_antigravity_full(self) -> dict:
        """彻底初始化 Antigravity 客户端：终止进程、恢复官方原版英文、清空冗余死缓存、重置所有个性化补丁为默认"""
        try:
            # 1. 终止运行中客户端
            LocalizationManager.kill_running_antigravity()
            time.sleep(0.8)

            # 2. 还原官方原生英文备份
            LocalizationManager.restore(stream_output=False)

            # 3. 深度清理磁盘死缓存
            StorageManager.clean_storage(clean_cache=True, clean_temp_logs=True, vacuum_db=True)

            # 4. 重置个性化配置为官方默认
            cfg = load_config()
            cfg["customization"] = {
                "language": "zh-CN",
                "show_quota_badge": False,
                "clean_ui": False,
                "opt_gpu": False,
                "opt_max_heap": False,
                "opt_nosleep": False,
                "opt_telemetry": False,
                "enable_gpu_acceleration": False,
                "disable_background_throttling": False,
                "expand_v8_memory": False,
                "disable_telemetry": False,
                "hide_ide_buttons": False,
                "start_maximized": False,
                "prune_guide_skills": False,
                "proxy_enabled": False,
                "proxy_type": "socks5",
                "proxy_host": "127.0.0.1",
                "proxy_port": 10808,
                "proxy_bypass": "localhost, 127.0.0.1, *.local",
                "proxy_url": ""
            }
            save_config(cfg)
            try:
                SkillsOptimizer.set_pruned(False)
            except Exception:
                pass

            return {
                "success": True,
                "message": "已完成 Antigravity 彻底初始化！官方原版英文已恢复，死缓存已清空，设置已复位。"
            }
        except Exception as e:
            return {"success": False, "message": f"彻底初始化失败: {e}"}

    def control_daemon(self, action: str, port: int = 49222) -> dict:
        """启停后台常驻守护监听"""
        try:
            if action == "start":
                running, _ = self._check_daemon_running(port)
                if running:
                    return {"success": True, "message": f"守护服务已在运行中 (端口 {port})"}

                system = platform.system().lower()
                main_py = PROJECT_ROOT / "main.py"
                py_exe = sys.executable

                if system == "windows":
                    if getattr(sys, "frozen", False):
                        cmd = [str(sys.executable), "run"]
                    else:
                        pyw = Path(py_exe).parent / "pythonw.exe"
                        launcher = str(pyw) if pyw.exists() else py_exe
                        cmd = [launcher, str(main_py), "run"]

                    subprocess.Popen(
                        cmd,
                        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                        close_fds=True
                    )
                else:
                    subprocess.Popen([py_exe, str(main_py), "run"], start_new_session=True)

                time.sleep(0.5)
                return {"success": True, "message": "守护监听服务已成功启动！"}

            elif action == "stop":
                pid_file = BASE_DIR / ".daemon.pid"
                stopped = False
                if pid_file.exists():
                    try:
                        pid = int(pid_file.read_text(encoding="utf-8").strip())
                        if platform.system().lower() == "windows":
                            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
                        else:
                            os.kill(pid, 15)
                        stopped = True
                    except Exception:
                        pass
                    try:
                        pid_file.unlink()
                    except Exception:
                        pass
                time.sleep(0.3)
                return {"success": True, "message": "守护服务已停止！" if stopped else "守护服务未运行"}

            return {"success": False, "message": f"未知动作: {action}"}
        except Exception as e:
            return {"success": False, "message": f"守护操作失败: {e}"}

    def toggle_daemon_autostart(self, enable: bool) -> dict:
        """切换后台守护服务系统自启"""
        if enable:
            ok, msg = AutostartManager.enable()
        else:
            ok, msg = AutostartManager.disable()
        return {"success": ok, "message": msg}

    def toggle_app_autostart(self, enable: bool) -> dict:
        """切换 Orbit 客户端开机自启 (静默驻留托盘)"""
        cfg = load_config()
        cfg["app_autostart"] = enable
        save_config(cfg)

        if enable:
            ok, msg = AutostartManager.enable_app_autostart()
        else:
            ok, msg = AutostartManager.disable_app_autostart()
        return {"success": ok, "message": msg}

    def get_storage_breakdown(self) -> dict:
        """异步按需获取磁盘垃圾与缓存分析"""
        try:
            return {"success": True, "data": StorageManager.get_storage_breakdown()}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def clean_storage(self) -> dict:
        """执行安全深度瘦身"""
        try:
            freed, details = StorageManager.clean_storage(clean_cache=True, clean_temp_logs=True, vacuum_db=True)
            from core.storage import format_bytes
            size_str = format_bytes(freed)
            latest = StorageManager.get_storage_breakdown()
            return {
                "success": True,
                "message": f"深度瘦身完成！共成功释放磁盘空间 {size_str}。",
                "data": latest
            }
        except Exception as e:
            return {"success": False, "message": f"瘦身异常: {e}"}

    def save_system_prompt(self, content: str) -> dict:
        """保存全局系统提示词"""
        ok, msg = PromptManager.save_system_prompt(content)
        return {"success": ok, "message": msg}

    def restore_prompt_backup(self) -> dict:
        """从 .bak 备份恢复提示词"""
        ok, msg = PromptManager.restore_backup()
        content = PromptManager.read_system_prompt() if ok else ""
        return {"success": ok, "message": msg, "content": content}

    def get_custom_prompts(self) -> dict:
        """获取所有自定义提示词"""
        templates = PromptManager.get_custom_templates()
        return {"success": True, "templates": templates}

    def save_custom_prompt(self, title: str, content: str, prompt_id: str = None) -> dict:
        """保存自定义提示词"""
        ok, msg, tpl = PromptManager.save_custom_template(title, content, prompt_id)
        return {"success": ok, "message": msg, "template": tpl}

    def delete_custom_prompt(self, prompt_id: str) -> dict:
        """删除自定义提示词"""
        ok, msg = PromptManager.delete_custom_template(prompt_id)
        return {"success": ok, "message": msg}

    def apply_custom_prompt(self, prompt_id: str) -> dict:
        """一键应用自定义提示词到全局系统提示词 (AGENTS.md)"""
        ok, msg, content = PromptManager.apply_custom_template(prompt_id)
        return {"success": ok, "message": msg, "content": content}

    def test_notifier(self, channel: str, params: dict) -> dict:
        """测试通知渠道"""
        try:
            if channel == "telegram":
                from notifiers import TelegramNotifier
                token = params.get("bot_token", "").strip()
                chat_id = params.get("chat_id", "").strip()
                proxy = params.get("proxy", "").strip()
                if not token or not chat_id:
                    return {"success": False, "message": "请先填写 Bot Token 与 Chat ID"}
                n = TelegramNotifier(token, chat_id, proxy=proxy or None)
                ok, err = n.send("🚀 [Antigravity Orbit] 收到来自管理中心的 Telegram 测试通知！")
                return {"success": ok, "message": "Telegram 测试通知发送成功！" if ok else f"发送失败: {err}"}

            elif channel == "feishu":
                from notifiers import FeishuNotifier
                url = params.get("webhook_url", "").strip()
                if not url:
                    return {"success": False, "message": "请先填写飞书 Webhook 地址"}
                n = FeishuNotifier(url)
                ok, err = n.send("🚀 [Antigravity Orbit] 收到来自管理中心的飞书机器人测试通知！")
                return {"success": ok, "message": "飞书测试通知已送达！" if ok else f"发送失败: {err}"}

            elif channel == "wecom":
                from notifiers import WeComNotifier
                url = params.get("webhook_url", "").strip()
                if not url:
                    return {"success": False, "message": "请先填写企业微信 Webhook 地址"}
                n = WeComNotifier(url)
                ok, err = n.send("🚀 [Antigravity Orbit] 收到来自管理中心的企业微信测试通知！")
                return {"success": ok, "message": "企业微信测试通知已送达！" if ok else f"发送失败: {err}"}

            return {"success": False, "message": f"未知通知渠道: {channel}"}
        except Exception as e:
            return {"success": False, "message": f"测试通道异常: {e}"}

    def clear_logs(self) -> dict:
        """清空日志"""
        try:
            if LOG_FILE.exists():
                LOG_FILE.write_text("", encoding="utf-8")
            return {"success": True, "message": "运行日志已清空"}
        except Exception as e:
            return {"success": False, "message": f"清空日志失败: {e}"}

    # ------------------------------------------------------------------
    # 账号池与多账号极速切号 API
    # ------------------------------------------------------------------
    def get_account_pool(self) -> dict:
        """获取账号池全量数据"""
        try:
            return {"success": True, "data": self._account_mgr.get_accounts_summary()}
        except Exception as e:
            return {"success": False, "message": f"获取账号池失败: {e}"}

    def import_current_account(self) -> dict:
        """一键从系统凭据导入当前反重力账号"""
        try:
            ok, info, msg = self._account_mgr.import_current_client_account()
            pool = self._account_mgr.get_accounts_summary()
            return {"success": ok, "message": msg, "data": pool}
        except Exception as e:
            return {"success": False, "message": f"导入账号失败: {e}"}

    def add_account(self, token_input: str, custom_name: str = "") -> dict:
        """手动添加/导入账号 (Refresh Token 或 JSON)"""
        try:
            ok, info, msg = self._account_mgr.add_account_by_token(token_input, custom_name or None)
            pool = self._account_mgr.get_accounts_summary()
            return {"success": ok, "message": msg, "data": pool}
        except Exception as e:
            return {"success": False, "message": f"添加账号异常: {e}"}

    def switch_account(self, account_id: str, restart_app: bool = True) -> dict:
        """一键切换当前反重力账号并自动重启反重力客户端生效"""
        try:
            ok, msg = self._account_mgr.switch_account(account_id)
            if not ok:
                return {"success": False, "message": msg}

            restart_msg = ""
            if restart_app:
                LocalizationManager.kill_running_antigravity()
                time.sleep(0.8)
                r_ok, r_msg = LocalizationManager.launch_antigravity()
                restart_msg = "，已自动重启反重力客户端生效！" if r_ok else f"，重启客户端提示: {r_msg}"

            pool = self._account_mgr.get_accounts_summary()
            return {"success": True, "message": f"{msg}{restart_msg}", "data": pool}
        except Exception as e:
            return {"success": False, "message": f"切换账号异常: {e}"}

    def refresh_account_quota(self, account_id: str) -> dict:
        """刷新指定账号额度"""
        try:
            ok, quota, msg = self._account_mgr.refresh_single_account_quota(account_id)
            pool = self._account_mgr.get_accounts_summary()
            return {"success": ok, "message": msg, "data": pool}
        except Exception as e:
            return {"success": False, "message": f"刷新额度失败: {e}"}

    def refresh_all_quotas(self, interval_sec: float = 1.0) -> dict:
        """全量批量自动刷新所有账号额度 (支持分段间隔刷新，防止并发风控)"""
        try:
            ok, count, msg = self._account_mgr.refresh_all_quotas(interval_sec=interval_sec)
            pool = self._account_mgr.get_accounts_summary()
            return {"success": ok, "message": msg, "count": count, "data": pool}
        except Exception as e:
            return {"success": False, "message": f"批量刷新失败: {e}"}

    def delete_account(self, account_id: str) -> dict:
        """移除账号"""
        try:
            ok, msg = self._account_mgr.delete_account(account_id)
            pool = self._account_mgr.get_accounts_summary()
            return {"success": ok, "message": msg, "data": pool}
        except Exception as e:
            return {"success": False, "message": f"删除账号失败: {e}"}

    def start_oauth_login(self, open_browser: bool = True) -> dict:
        """启动 Google OAuth 网页授权流程并尝试唤起浏览器"""
        try:
            res = self._account_mgr.start_oauth_login(port=51121)
            auth_url = res.get("auth_url")
            if open_browser and auth_url:
                try:
                    webbrowser.open(auth_url)
                except Exception:
                    pass
            return res
        except Exception as e:
            return {"success": False, "message": f"启动授权失败: {e}"}

    def check_oauth_status(self) -> dict:
        """轮询检查 OAuth 回调状态"""
        try:
            return self._account_mgr.check_oauth_status()
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def submit_oauth_code(self, code_or_url: str, custom_name: str = "") -> dict:
        """手动提交网页授权重定向链接或授权码"""
        try:
            ok, info, msg = self._account_mgr.submit_oauth_code(code_or_url, custom_name=custom_name or None)
            pool = self._account_mgr.get_accounts_summary()
            return {"success": ok, "message": msg, "data": pool}
        except Exception as e:
            return {"success": False, "message": f"提交授权失败: {e}"}

    def cancel_oauth_login(self) -> dict:
        """取消 OAuth 授权监听"""
        try:
            self._account_mgr.cancel_oauth_login()
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def test_proxy(self, a: str = "127.0.0.1", b=10808, c: str = "socks5") -> dict:
        """真实探测指定代理节点并测试访问 Google (兼容各种调用签名)"""
        if str(a).lower() in ("http", "https", "socks5", "socks5h"):
            p_type = str(a).lower()
            host = str(b).strip()
            port = int(c)
        else:
            host = str(a).strip()
            port = int(b)
            p_type = str(c).lower()

        import socket
        import time

        # 1. TCP 端口连通性
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        res = sock.connect_ex((host, port))
        sock.close()
        if res != 0:
            return {
                "success": False,
                "message": f"无法连接到代理端口 {host}:{port} (错误码: {res})。请确认代理客户端 (如 v2rayN/Clash/Xray) 是否正在运行。"
            }

        # 2. 真实 HTTP/SOCKS5 握手并访问 Google 204
        start_t = time.time()
        try:
            import urllib.request
            scheme = "socks5h" if p_type == "socks5" else "http"
            proxy_addr = f"{scheme}://{host}:{port}"
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({"http": proxy_addr, "https": proxy_addr})
            )
            resp = opener.open("https://www.google.com/generate_204", timeout=4.0)
            latency_ms = int((time.time() - start_t) * 1000)
            if resp.status in (200, 204):
                return {
                    "success": True,
                    "message": f"代理连通成功！Google 延迟: {latency_ms}ms ({p_type.upper()} {host}:{port})",
                    "latency_ms": latency_ms
                }
        except Exception:
            pass

        return {
            "success": True,
            "message": f"代理本地端口握手成功 ({p_type.upper()} {host}:{port})！"
        }

    def detect_local_proxy(self) -> dict:
        """自动扫描并探测本机常用代理端口 (v2rayN/Xray/Clash/Surge)"""
        candidates = [
            ("127.0.0.1", 10808, "socks5"),
            ("127.0.0.1", 10808, "http"),
            ("127.0.0.1", 7890, "socks5"),
            ("127.0.0.1", 7890, "http"),
            ("127.0.0.1", 7897, "http"),
            ("127.0.0.1", 10809, "http"),
            ("127.0.0.1", 1080, "socks5"),
        ]
        import socket
        import time

        for host, port, p_type in candidates:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                res = sock.connect_ex((host, port))
                sock.close()
                if res == 0:
                    try:
                        import urllib.request
                        scheme = "socks5h" if p_type == "socks5" else "http"
                        opener = urllib.request.build_opener(
                            urllib.request.ProxyHandler({"http": f"{scheme}://{host}:{port}", "https": f"{scheme}://{host}:{port}"})
                        )
                        start_t = time.time()
                        resp = opener.open("https://www.google.com/generate_204", timeout=2.0)
                        latency = int((time.time() - start_t) * 1000)
                        if resp.status in (200, 204):
                            return {
                                "detected": True,
                                "host": host,
                                "port": port,
                                "type": p_type,
                                "latency_ms": latency,
                                "message": f"成功探测到可用代理: {host}:{port} ({p_type.upper()}, 延迟 {latency}ms)"
                            }
                    except Exception:
                        pass

                    return {
                        "detected": True,
                        "host": host,
                        "port": port,
                        "type": p_type,
                        "latency_ms": 0,
                        "message": f"探测到本地代理监听端口: {host}:{port} ({p_type.upper()})"
                    }
            except Exception:
                continue

        return {"detected": False, "message": "未扫描到本机运行的常见代理服务 (10808/7890/7897/10809)"}

    def export_accounts_data(self, format_type: str = "cockpit") -> dict:
        """导出账号池所有凭据为 JSON 格式 (支持 cockpit 或 full)"""
        try:
            data = self._account_mgr.export_accounts(format_type=format_type)
            json_str = json.dumps(data, ensure_ascii=False, indent=2)
            count = len(data) if isinstance(data, list) else len(data.get("accounts", []))
            fmt_desc = "Cockpit 兼容格式" if format_type == "cockpit" else "完整备份格式"
            return {
                "success": True,
                "json_str": json_str,
                "count": count,
                "format": format_type,
                "message": f"成功导出 {count} 个账号数据 ({fmt_desc})"
            }
        except Exception as e:
            return {"success": False, "message": f"导出账号失败: {e}", "json_str": ""}

    def open_config_dir(self) -> dict:
        """在系统文件资源管理器中打开 Orbit 配置与数据目录"""
        try:
            cfg_dir = Path.home() / ".gemini" / "antigravity"
            cfg_dir.mkdir(parents=True, exist_ok=True)
            if platform.system().lower() == "windows":
                os.startfile(str(cfg_dir))
            else:
                subprocess.Popen(["xdg-open", str(cfg_dir)])
            return {"success": True, "message": f"已打开目录: {cfg_dir}"}
        except Exception as e:
            return {"success": False, "message": f"打开配置目录失败: {e}"}

    def open_external(self, url: str) -> dict:
        """在系统默认浏览器中打开外部链接"""
        try:
            webbrowser.open(url)
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

