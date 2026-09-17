import os
import sys
import platform
from pathlib import Path

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
