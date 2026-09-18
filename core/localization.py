import os
import sys
import json
import shutil
import platform
import subprocess
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from core.config import RESOURCE_DIR, CONFIG_FILE

# 项目静态资源目录与本地化目录
LOCALIZATION_DIR = RESOURCE_DIR / "localization"
ENGINE_SCRIPT = LOCALIZATION_DIR / "engine.js"

class LocalizationManager:
    """Antigravity 界面汉化与本地化管理核心类"""

    @staticmethod
    def _run_subp(cmd, cwd=None, capture_output=True, timeout=None):
        """跨平台执行子进程，Windows 下强力抑制黑控制台窗口弹出"""
        kwargs = {"cwd": str(cwd) if cwd else None}
        if timeout:
            kwargs["timeout"] = timeout
        if capture_output:
            kwargs["capture_output"] = True
            kwargs["text"] = True
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE
            kwargs["startupinfo"] = startupinfo
        return subprocess.run(cmd, **kwargs)

    @classmethod
    def check_node_environment(cls, fast: bool = True) -> Tuple[bool, str]:
        """检测系统是否存在 Node.js 环境 (fast=True 仅探测 PATH，0毫秒无开销)"""
        node_exe = shutil.which("node")
        if not node_exe:
            return False, "未在系统中检测到 Node.js 环境"
        if fast:
            return True, "已就绪"
        try:
            res = cls._run_subp([node_exe, "-v"], capture_output=True, timeout=5)
            version = (res.stdout or "").strip()
            return True, version
        except Exception as e:
            return False, f"检测 Node.js 异常: {e}"

    @classmethod
    def get_status(cls, install_dir: Optional[str] = None, fast: bool = True) -> Dict[str, Any]:
        """获取 Antigravity 客户端及其汉化状态 (默认极速秒级纯 Python 检测)"""
        node_ok, node_ver = cls.check_node_environment(fast=fast)

        status: Dict[str, Any] = {
            "installed": False,
            "install_dir": "",
            "resources_dir": "",
            "is_v2": False,
            "is_localized": False,
            "lang": None,
            "has_backup": False,
            "node_available": node_ok,
            "node_version": node_ver if node_ok else None,
        }

        # 快速纯 Python 检测 (毫秒级响应，无子进程阻塞)
        found_dir = cls._fallback_detect_dir(install_dir)
        if found_dir and Path(found_dir).exists():
            status["installed"] = True
            status["install_dir"] = str(found_dir)

            res_dir = Path(found_dir) / "resources"
            if not res_dir.exists():
                res_dir = Path(found_dir) / "Contents" / "Resources"
            if not res_dir.exists():
                res_dir = Path(found_dir)

            status["resources_dir"] = str(res_dir)
            asar = res_dir / "app.asar"
            asar_bak = res_dir / "app.asar.bak"
            meta_file = res_dir / ".localization_info.json"

            status["is_v2"] = asar.exists()
            status["has_backup"] = asar_bak.exists()

            if meta_file.exists():
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                        status["is_localized"] = bool(meta.get("localized", False))
                        status["lang"] = meta.get("lang")
                except Exception:
                    pass
            elif asar_bak.exists():
                status["is_localized"] = True
                status["lang"] = "zh-CN"

            if fast:
                return status

        # 若 fast=False，才通过 node engine.js 深入检测
        if not fast and node_ok and ENGINE_SCRIPT.exists():
            cmd = ["node", str(ENGINE_SCRIPT), "--status", "--json"]
            if CONFIG_FILE.exists():
                cmd.extend(["--config-file", str(CONFIG_FILE)])
            if install_dir:
                cmd.extend(["--install-dir", install_dir])
            try:
                res = cls._run_subp(cmd, capture_output=True, timeout=10, cwd=str(RESOURCE_DIR))
                if res.returncode == 0:
                    data = json.loads(res.stdout.strip())
                    status["installed"] = data.get("installed", False)
                    status["install_dir"] = data.get("installDir", "")
                    status["resources_dir"] = data.get("resourcesDir", "")
                    status["is_v2"] = data.get("isV2", False)
                    status["is_localized"] = data.get("isLocalized", False)
                    status["lang"] = data.get("lang")
                    status["has_backup"] = data.get("hasBackup", False)
                    return status
            except Exception:
                pass

        return status

    @classmethod
    def install(
        cls,
        tw: bool = False,
        en: bool = False,
        install_dir: Optional[str] = None,
        no_kill: bool = False,
        stream_output: bool = True
    ) -> Tuple[bool, str]:
        """安装或更新汉化包与优化配置 (强力抑制黑窗口)"""
        node_ok, node_msg = cls.check_node_environment()
        if not node_ok:
            return False, f"无法执行部署: {node_msg}。\n请先安装 Node.js (https://nodejs.org) 并配置 PATH。"

        if not ENGINE_SCRIPT.exists():
            return False, f"未找到核心汉化引擎脚本: {ENGINE_SCRIPT}"

        cmd = ["node", str(ENGINE_SCRIPT)]
        if tw:
            cmd.append("--tw")
        elif en:
            cmd.append("--en")
        if CONFIG_FILE.exists():
            cmd.extend(["--config-file", str(CONFIG_FILE)])
        if install_dir:
            cmd.extend(["--install-dir", install_dir])
        if no_kill:
            cmd.append("--no-kill")

        try:
            res = cls._run_subp(cmd, cwd=str(RESOURCE_DIR), capture_output=True)
            output = (res.stdout or "") + ("\n" + res.stderr if res.stderr else "")
            return (res.returncode == 0, output.strip() if output.strip() else ("部署成功" if res.returncode == 0 else "部署失败"))
        except Exception as e:
            return False, f"执行汉化引擎异常: {e}"

    @classmethod
    def restore(
        cls,
        install_dir: Optional[str] = None,
        no_kill: bool = False,
        stream_output: bool = True
    ) -> Tuple[bool, str]:
        """卸载汉化，恢复官方原版英文 (强力抑制黑窗口)"""
        node_ok, node_msg = cls.check_node_environment()
        if not node_ok:
            return False, f"无法还原官方英文: {node_msg}。"

        if not ENGINE_SCRIPT.exists():
            return False, f"未找到核心汉化引擎脚本: {ENGINE_SCRIPT}"

        cmd = ["node", str(ENGINE_SCRIPT), "--restore"]
        if install_dir:
            cmd.extend(["--install-dir", install_dir])
        if no_kill:
            cmd.append("--no-kill")

        try:
            res = cls._run_subp(cmd, cwd=str(RESOURCE_DIR), capture_output=True)
            output = (res.stdout or "") + ("\n" + res.stderr if res.stderr else "")
            return (res.returncode == 0, "官方原版英文已成功恢复！" if res.returncode == 0 else f"恢复失败: {output.strip()}")
        except Exception as e:
            return False, f"执行还原操作异常: {e}"

    @classmethod
    def is_running(cls) -> bool:
        """检查 Antigravity 客户端是否正在运行"""
        try:
            if sys.platform == "win32":
                res = cls._run_subp(["tasklist", "/fi", "imagename eq Antigravity.exe", "/nh"], capture_output=True)
                return "antigravity.exe" in (res.stdout or "").lower()
            elif sys.platform == "darwin":
                res = cls._run_subp(["pgrep", "-f", "Antigravity"], capture_output=True)
                return res.returncode == 0
        except Exception:
            pass
        return False

    @classmethod
    def kill_running_antigravity(cls) -> bool:
        """安全终止运行中的 Antigravity 客户端"""
        try:
            if sys.platform == "win32":
                cls._run_subp(["taskkill", "/F", "/IM", "Antigravity.exe"], capture_output=True)
            elif sys.platform == "darwin":
                cls._run_subp(["pkill", "-f", "Antigravity"], capture_output=True)
            return True
        except Exception:
            return False

    @classmethod
    def launch_antigravity(cls, install_dir: Optional[str] = None) -> Tuple[bool, str]:
        """拉起启动 Antigravity 客户端"""
        target_dir = cls._fallback_detect_dir(install_dir)
        if not target_dir:
            return False, "未能探测到 Antigravity 安装目录"

        try:
            if sys.platform == "win32":
                exe_path = Path(target_dir) / "Antigravity.exe"
                if exe_path.exists():
                    subprocess.Popen(
                        [str(exe_path)],
                        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
                        close_fds=True
                    )
                    return True, "已启动 Antigravity 客户端"
            elif sys.platform == "darwin":
                cls._run_subp(["open", str(target_dir)], capture_output=True)
                return True, "已启动 Antigravity 客户端"
        except Exception as e:
            return False, f"拉起客户端失败: {e}"
        return False, "未找到客户端可执行文件"


    @staticmethod
    def _fallback_detect_dir(manual_dir: Optional[str] = None) -> Optional[Path]:
        """跨平台备选路径探测"""
        if manual_dir and Path(manual_dir).exists():
            p = Path(manual_dir).resolve()
            if p.is_file() and p.name == "app.asar":
                p = p.parent
            return p

        candidates = []
        sys_name = platform.system().lower()

        if sys_name == "windows":
            # 常见 Windows 目录
            for drive in ["C", "D", "E", "F"]:
                candidates.append(Path(f"{drive}:/Programs/Antigravity"))
                candidates.append(Path(f"{drive}:/Antigravity"))
            candidates.append(Path("C:/Program Files/Antigravity"))
            local_appdata = os.environ.get("LOCALAPPDATA")
            if local_appdata:
                candidates.append(Path(local_appdata) / "Programs" / "antigravity")

        elif sys_name == "darwin":
            candidates.append(Path("/Applications/Antigravity.app"))
            candidates.append(Path.home() / "Applications" / "Antigravity.app")

        for c in candidates:
            if c.exists():
                if (c / "resources" / "app.asar").exists() or (c / "app.asar").exists() or (c / "Contents" / "Resources" / "app.asar").exists():
                    return c
        return None

    @classmethod
    def format_status(cls, status: Dict[str, Any]) -> str:
        """格式化展示状态报告"""
        lines = [
            "=" * 50,
            "🌐【Google Antigravity 客户端与汉化状态】",
            "=" * 50,
        ]

        if not status.get("installed"):
            lines.append("• 客户端状态: 🔴 未检测到 Antigravity 安装目录")
            lines.append("  (提示: 如果已安装，请使用 --dir 参数指定客户端安装路径)")
        else:
            lines.append(f"• 软件路径: {status.get('install_dir')}")
            arch = "Antigravity 2.0+ (ASAR)" if status.get("is_v2") else "Antigravity 1.0 (HTML)"
            lines.append(f"• 架构类型: {arch}")

            is_loc = status.get("is_localized")
            lang = status.get("lang")
            lang_str = "繁体中文 (zh-TW)" if lang == "zh-TW" else ("简体中文 (zh-CN)" if lang == "zh-CN" else "中文语言包")
            brand = status.get("brand_title") or "english"

            if is_loc:
                lines.append(f"• 界面语言: 🟢 已汉化 [{lang_str}]")
            else:
                lines.append("• 界面语言: ⚪ 官方原版英文")

            backup = "🟢 存在 (可随时一键卸载还原)" if status.get("has_backup") else "⚪ 未创建"
            lines.append(f"• 原始备份: {backup}")

        node_ok = status.get("node_available")
        node_ver = status.get("node_version") or "未安装"
        lines.append(f"• Node.js 环境: {'🟢 ' + node_ver if node_ok else '🔴 未检测到 (需安装以执行注入)'}")
        lines.append("=" * 50)
        return "\n".join(lines)
