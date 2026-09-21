import os
import sys
import platform
from pathlib import Path
from typing import Optional

class AutostartManager:
    @staticmethod
    def get_os():
        return platform.system().lower()

    @staticmethod
    def is_enabled() -> bool:
        system = AutostartManager.get_os()
        if system == "windows":
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
                winreg.QueryValueEx(key, "AntigravityNotifier")
                winreg.CloseKey(key)
                return True
            except Exception:
                return False
        elif system == "darwin":
            plist_path = Path.home() / "Library" / "LaunchAgents" / "com.antigravity.notifier.plist"
            return plist_path.exists()
        elif system == "linux":
            service_path = Path.home() / ".config" / "systemd" / "user" / "antigravity-notifier.service"
            return service_path.exists()
        return False

    @staticmethod
    def enable() -> tuple[bool, str]:
        system = AutostartManager.get_os()
        main_py = Path(__file__).resolve().parent.parent / "main.py"
        python_exe = sys.executable

        if system == "windows":
            # 在 Windows 上，寻找 pythonw.exe 避免控制台黑框弹出
            pythonw_exe = Path(python_exe).parent / "pythonw.exe"
            runner_exe = str(pythonw_exe) if pythonw_exe.exists() else python_exe
            cmd = f'"{runner_exe}" "{main_py}" run'
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, "AntigravityNotifier", 0, winreg.REG_SZ, cmd)
                winreg.CloseKey(key)
                return True, "已成功写入 Windows 注册表开机启动项"
            except Exception as e:
                return False, f"写入注册表失败: {e}"

        elif system == "darwin":
            launch_dir = Path.home() / "Library" / "LaunchAgents"
            launch_dir.mkdir(parents=True, exist_ok=True)
            plist_path = launch_dir / "com.antigravity.notifier.plist"
            plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.antigravity.notifier</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_exe}</string>
        <string>{main_py}</string>
        <string>run</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
"""
            try:
                with open(plist_path, "w", encoding="utf-8") as f:
                    f.write(plist_content)
                os.system(f"launchctl load {plist_path} >/dev/null 2>&1")
                return True, f"已生成 macOS LaunchAgent: {plist_path}"
            except Exception as e:
                return False, f"配置 macOS 开机启动失败: {e}"

        elif system == "linux":
            systemd_dir = Path.home() / ".config" / "systemd" / "user"
            systemd_dir.mkdir(parents=True, exist_ok=True)
            service_path = systemd_dir / "antigravity-notifier.service"
            service_content = f"""[Unit]
Description=Antigravity Task Completion Notifier
After=network.target

[Service]
Type=simple
ExecStart={python_exe} {main_py} run
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
"""
            try:
                with open(service_path, "w", encoding="utf-8") as f:
                    f.write(service_content)
                os.system("systemctl --user daemon-reload && systemctl --user enable antigravity-notifier")
                return True, f"已注册 Linux systemd 用户服务: {service_path}"
            except Exception as e:
                return False, f"配置 Linux systemd 服务失败: {e}"

        return False, f"不支持的操作系统: {system}"

    @staticmethod
    def disable() -> tuple[bool, str]:
        system = AutostartManager.get_os()
        if system == "windows":
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
                winreg.DeleteValue(key, "AntigravityNotifier")
                winreg.CloseKey(key)
                return True, "已成功移除 Windows 注册表开机启动项"
            except Exception as e:
                return False, f"移除注册表项失败: {e}"
        elif system == "darwin":
            plist_path = Path.home() / "Library" / "LaunchAgents" / "com.antigravity.notifier.plist"
            if plist_path.exists():
                os.system(f"launchctl unload {plist_path} >/dev/null 2>&1")
                plist_path.unlink()
                return True, "已注销 macOS 开机启动项"
            return True, "开机启动项不存在"
        elif system == "linux":
            service_path = Path.home() / ".config" / "systemd" / "user" / "antigravity-notifier.service"
            if service_path.exists():
                os.system("systemctl --user disable antigravity-notifier")
                service_path.unlink()
                os.system("systemctl --user daemon-reload")
                return True, "已注销 Linux systemd 服务"
            return True, "服务不存在"
        return False, f"不支持的操作系统: {system}"

    @staticmethod
    def is_app_autostart_enabled() -> bool:
        """检查 Orbit 管理中心客户端是否配置了开机自启 (同时校验目标程序是否真实存在)"""
        system = AutostartManager.get_os()
        if system == "windows":
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
                val, _ = winreg.QueryValueEx(key, "AntigravityOrbitApp")
                winreg.CloseKey(key)
                if val:
                    val_str = str(val).strip()
                    if val_str.startswith('"'):
                        clean_path = val_str[1:].split('"')[0]
                    else:
                        clean_path = val_str.split()[0]
                    if Path(clean_path).exists():
                        return True
                return False
            except Exception:
                return False
        elif system == "darwin":
            plist_path = Path.home() / "Library" / "LaunchAgents" / "com.antigravity.orbit.app.plist"
            return plist_path.exists()
        elif system == "linux":
            autostart_path = Path.home() / ".config" / "autostart" / "antigravity-orbit.desktop"
            return autostart_path.exists()
        return False

    @staticmethod
    def _find_installed_app_exe() -> Optional[Path]:
        """探测已安装的 Antigravity-Orbit 客户端可执行文件 (兼容打包与安装模式)"""
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve()

        # 1. 尝试从注册表读取 Inno Setup 安装目录
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\AntigravityOrbit", 0, winreg.KEY_READ)
            inst_dir, _ = winreg.QueryValueEx(key, "InstallLocation")
            winreg.CloseKey(key)
            if inst_dir:
                p = Path(inst_dir) / "Antigravity-Orbit.exe"
                if p.exists():
                    return p.resolve()
        except Exception:
            pass

        # 2. 尝试标准安装目录与常见目录
        local_app = os.environ.get("LOCALAPPDATA", "")
        candidates = [
            Path(local_app) / "Programs" / "Antigravity-Orbit" / "Antigravity-Orbit.exe" if local_app else None,
            Path("D:/Antigravity-Orbit/Antigravity-Orbit.exe"),
            Path("C:/Program Files/Antigravity-Orbit/Antigravity-Orbit.exe"),
        ]
        for c in candidates:
            if c and c.exists():
                return c.resolve()
        return None

    @staticmethod
    def enable_app_autostart() -> tuple[bool, str]:
        """启用 Orbit 客户端开机自启 (开机以 --tray 参数静默驻留托盘)"""
        system = AutostartManager.get_os()
        is_frozen = getattr(sys, "frozen", False)
        python_exe = sys.executable

        if system == "windows":
            if is_frozen:
                cmd = f'"{python_exe}" --tray'
            else:
                exe_target = AutostartManager._find_installed_app_exe()
                if exe_target:
                    cmd = f'"{exe_target}" --tray'
                else:
                    pythonw_exe = Path(python_exe).parent / "pythonw.exe"
                    runner_exe = str(pythonw_exe) if pythonw_exe.exists() else python_exe
                    main_py = Path(__file__).resolve().parent.parent / "main.py"
                    cmd = f'"{runner_exe}" "{main_py}" gui --tray'
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, "AntigravityOrbitApp", 0, winreg.REG_SZ, cmd)
                winreg.CloseKey(key)
                return True, "已成功设置 Orbit 客户端开机自启 (开机自动静默驻留系统托盘)"
            except Exception as e:
                return False, f"写入注册表失败: {e}"

        elif system == "darwin":
            launch_dir = Path.home() / "Library" / "LaunchAgents"
            launch_dir.mkdir(parents=True, exist_ok=True)
            plist_path = launch_dir / "com.antigravity.orbit.app.plist"
            if is_frozen:
                prog_args = f"<string>{python_exe}</string>\n        <string>--tray</string>"
            else:
                main_py = Path(__file__).resolve().parent.parent / "main.py"
                prog_args = f"<string>{python_exe}</string>\n        <string>{main_py}</string>\n        <string>gui</string>\n        <string>--tray</string>"

            plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.antigravity.orbit.app</string>
    <key>ProgramArguments</key>
    <array>
        {prog_args}
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
"""
            try:
                with open(plist_path, "w", encoding="utf-8") as f:
                    f.write(plist_content)
                os.system(f"launchctl load {plist_path} >/dev/null 2>&1")
                return True, "已成功配置 macOS 客户端开机自启动项"
            except Exception as e:
                return False, f"配置 macOS 开机自启失败: {e}"

        elif system == "linux":
            autostart_dir = Path.home() / ".config" / "autostart"
            autostart_dir.mkdir(parents=True, exist_ok=True)
            desktop_path = autostart_dir / "antigravity-orbit.desktop"
            if is_frozen:
                exec_cmd = f"{python_exe} --tray"
            else:
                main_py = Path(__file__).resolve().parent.parent / "main.py"
                exec_cmd = f"{python_exe} {main_py} gui --tray"
            desktop_content = f"""[Desktop Entry]
Type=Application
Version=1.0
Name=Antigravity Orbit
Comment=Antigravity Orbit Management Center
Exec={exec_cmd}
Icon=utilities-system-monitor
Terminal=false
Categories=Utility;Development;
"""
            try:
                with open(desktop_path, "w", encoding="utf-8") as f:
                    f.write(desktop_content)
                return True, "已成功配置 Linux 客户端开机自启动桌面项"
            except Exception as e:
                return False, f"配置 Linux 自启动失败: {e}"

        return False, f"不支持的操作系统: {system}"

    @staticmethod
    def disable_app_autostart() -> tuple[bool, str]:
        """关闭 Orbit 客户端开机自启动"""
        system = AutostartManager.get_os()
        if system == "windows":
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
                winreg.DeleteValue(key, "AntigravityOrbitApp")
                winreg.CloseKey(key)
                return True, "已成功取消 Orbit 客户端开机自启动"
            except Exception as e:
                return False, f"移除注册表项失败: {e}"
        elif system == "darwin":
            plist_path = Path.home() / "Library" / "LaunchAgents" / "com.antigravity.orbit.app.plist"
            if plist_path.exists():
                os.system(f"launchctl unload {plist_path} >/dev/null 2>&1")
                plist_path.unlink()
                return True, "已成功取消 macOS 客户端开机启动"
            return True, "开机启动项不存在"
        elif system == "linux":
            desktop_path = Path.home() / ".config" / "autostart" / "antigravity-orbit.desktop"
            if desktop_path.exists():
                desktop_path.unlink()
                return True, "已成功取消 Linux 客户端开机启动"
            return True, "开机启动项不存在"
        return False, f"不支持的操作系统: {system}"

