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


class OrbitApi:
    """提供给前端 JS 调用的核心原生 API 接口"""

    def __init__(self, window_holder=None):
        self._window_holder = window_holder

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

        # 存储分析
        storage_info = None
        try:
            storage_info = StorageManager.get_storage_breakdown()
        except Exception:
            pass

        # 提示词与模板
        prompt_content = PromptManager.read_system_prompt()
        templates = [
            {
                "key": k,
                "name": v["name"],
                "desc": v["desc"],
                "content": v["content"]
            }
            for k, v in PromptManager.TEMPLATES.items()
        ]

        # 运行日志最新 30 行
        logs = self._get_recent_logs()

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

    def save_and_apply(self, new_cfg: dict) -> dict:
        """保存配置并一键部署补丁"""
        try:
            cfg = load_config()
            cfg.update(new_cfg)
            save_config(cfg)

            # 更新 Skills 裁剪
            custom = cfg.get("customization", {})
            try:
                SkillsOptimizer.set_pruned(custom.get("prune_guide_skills", False))
            except Exception:
                pass

            # 部署补丁
            lang = custom.get("language", "zh-CN")
            is_tw = (lang == "zh-TW")
            is_en = (lang == "en")
            ok, msg = LocalizationManager.install(tw=is_tw, en=is_en, stream_output=False)

            return {
                "success": ok,
                "message": "配置与优化已成功部署生效！" if ok else f"部署失败: {msg}"
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
        """重启 Antigravity 客户端"""
        try:
            LocalizationManager.kill_running_antigravity()
            time.sleep(0.8)
            ok, msg = LocalizationManager.launch_antigravity()
            return {
                "success": ok,
                "message": "客户端已重新拉起！" if ok else f"未能自动拉起: {msg}"
            }
        except Exception as e:
            return {"success": False, "message": f"重启异常: {e}"}

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

    def clean_storage(self) -> dict:
        """执行安全深度瘦身"""
        try:
            freed, details = StorageManager.clean_storage(clean_cache=True, clean_temp_logs=True, vacuum_db=True)
            freed_mb = freed / (1024 * 1024)
            size_str = f"{freed / (1024 * 1024 * 1024):.2f} GB" if freed_mb >= 1024 else f"{freed_mb:.1f} MB"
            return {
                "success": True,
                "message": f"深度瘦身完成！共成功释放磁盘空间 {size_str}。"
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

    def open_external(self, url: str):
        """打开外部浏览器链接"""
        try:
            webbrowser.open(url)
        except Exception:
            pass
