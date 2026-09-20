# -*- coding: utf-8 -*-
"""
Antigravity Orbit - 原生 Windows 安装程序 (Native Windows Setup Wizard)
零第三方依赖、免管理员提权、自动创建桌面与开始菜单快捷方式、注册控制面板卸载项。
"""

import os
import sys
import time
import shutil
import zipfile
import winreg
import subprocess
from pathlib import Path

DEFAULT_INSTALL_DIR = Path.home() / "AppData" / "Local" / "Programs" / "Antigravity-Orbit"
APP_NAME = "Antigravity Orbit"
APP_VERSION = "3.3.4"
APP_PUBLISHER = "Antigravity Team"
EXE_NAME = "Antigravity-Orbit.exe"


def get_resource_path(relative_path: str) -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).resolve().parent / relative_path


def create_shortcut(target_path: Path, shortcut_path: Path, icon_path: Path = None, description: str = ""):
    """通过 Windows WScript.Shell 原生 COM 接口创建快捷方式"""
    try:
        target_str = str(target_path).replace('"', '`"')
        work_dir = str(target_path.parent).replace('"', '`"')
        icon_str = str(icon_path).replace('"', '`"') if icon_path else ""
        ps_script = f'''
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut("{shortcut_path}")
$s.TargetPath = "{target_str}"
$s.WorkingDirectory = "{work_dir}"
$s.Description = "{description}"
if ("{icon_str}" -and (Test-Path "{icon_str}")) {{
    $s.IconLocation = "{icon_str},0"
}} else {{
    $s.IconLocation = "{target_str},0"
}}
$s.Save()
'''
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        return True
    except Exception:
        return False


def get_previous_install_dir() -> Path:
    """读取注册表记录的历史安装目录，方便用户无缝升级更新不用额外选目录"""
    for root_key in [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]:
        for subkey in [
            r"Software\AntigravityOrbit",
            r"Software\Microsoft\Windows\CurrentVersion\Uninstall\AntigravityOrbit",
            r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{C8F8A77E-6564-42DF-A62E-0C4D9A0BC7E1}_is1",
        ]:
            try:
                with winreg.OpenKey(root_key, subkey) as key:
                    for val_name in ["InstallLocation", "InstallDir", "Path"]:
                        try:
                            val, _ = winreg.QueryValueEx(key, val_name)
                            if val and isinstance(val, str) and len(val.strip()) > 3:
                                p = Path(val.strip())
                                if p.exists() or p.parent.exists():
                                    return p
                        except Exception:
                            pass
            except Exception:
                pass
    return DEFAULT_INSTALL_DIR


def register_uninstall(install_dir: Path):
    """注册至 Windows 控制面板并在注册表记录安装路径供更新时自动识别"""
    try:
        # 1. 控制面板卸载项
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\AntigravityOrbit"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_NAME)
            winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)
            winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, APP_PUBLISHER)
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(install_dir))
            winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, str(install_dir / EXE_NAME) + ",0")
            winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{install_dir}\\uninstall.bat"')
            winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)

        # 2. 专用软件信息键 (供升级更新安装向导自动读取上一次安装目录)
        app_key_path = r"Software\AntigravityOrbit"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, app_key_path) as key:
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(install_dir))
            winreg.SetValueEx(key, "InstallDir", 0, winreg.REG_SZ, str(install_dir))
            winreg.SetValueEx(key, "Version", 0, winreg.REG_SZ, APP_VERSION)
    except Exception:
        pass



def write_uninstaller(install_dir: Path):
    """生成配套卸载脚本与注册表清理"""
    uninst_bat = install_dir / "uninstall.bat"
    desktop_lnk = Path.home() / "Desktop" / f"{APP_NAME}.lnk"
    start_menu_lnk = Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / f"{APP_NAME}.lnk"

    bat_content = f"""@echo off
chcp 65001 >nul
title 正在卸载 {APP_NAME}

echo 正在终止运行中的 {APP_NAME}...
taskkill /F /IM {EXE_NAME} 2>nul

echo 正在移除快捷方式...
if exist "{desktop_lnk}" del /f /q "{desktop_lnk}"
if exist "{start_menu_lnk}" del /f /q "{start_menu_lnk}"

echo 正在清理系统注册表...
reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\AntigravityOrbit" /f >nul 2>nul

echo 正在清理程序安装目录...
cd /d "%TEMP%"
rmdir /s /q "{install_dir}" 2>nul

echo.
echo {APP_NAME} 已成功从您的电脑中卸载。
timeout /t 2 >nul
exit /b 0
"""
    try:
        uninst_bat.write_text(bat_content, encoding="utf-8")
    except Exception:
        pass


def perform_installation(target_dir: Path, create_desktop: bool, create_start_menu: bool, progress_callback=None) -> tuple[bool, str]:
    """核心安装解压与注册流程"""
    payload_zip = get_resource_path("Antigravity-Orbit-Windows-x64.zip")
    if not payload_zip.exists():
        payload_zip = get_resource_path("app_payload.zip")
    if not payload_zip.exists():
        payload_zip = Path(__file__).resolve().parent.parent / "dist" / "Antigravity-Orbit-Windows-x64.zip"

    if not payload_zip.exists():
        return False, "未找到安装资源包 (Antigravity-Orbit-Windows-x64.zip)"

    if progress_callback: progress_callback(10, "正在关闭可能运行中的旧实例...")
    subprocess.run(f"taskkill /F /IM {EXE_NAME} 2>nul", shell=True, capture_output=True)
    time.sleep(0.5)

    if progress_callback: progress_callback(20, "正在准备安装目录...")
    target_dir.mkdir(parents=True, exist_ok=True)

    if progress_callback: progress_callback(30, "正在解压程序文件...")
    try:
        with zipfile.ZipFile(payload_zip, "r") as z:
            members = z.infolist()
            total = len(members)
            for i, member in enumerate(members):
                parts = Path(member.filename).parts
                if len(parts) > 1 and parts[0] == "Antigravity-Orbit":
                    rel_parts = parts[1:]
                elif len(parts) == 1 and parts[0] == "Antigravity-Orbit":
                    continue
                else:
                    rel_parts = parts
                
                if not rel_parts:
                    continue

                dest_file = target_dir.joinpath(*rel_parts)
                if member.is_dir():
                    dest_file.mkdir(parents=True, exist_ok=True)
                else:
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(member) as src, open(dest_file, "wb") as dst:
                        shutil.copyfileobj(src, dst)

                if progress_callback and i % 15 == 0:
                    pct = 30 + int((i / total) * 50)
                    progress_callback(pct, f"正在部署文件: {rel_parts[-1]}...")
    except Exception as e:
        return False, f"解压文件失败: {e}"

    app_exe = target_dir / EXE_NAME

    # 确保 target_dir/resources 目录存在并部署高清图标文件，杜绝桌面快捷方式空白
    res_dir = target_dir / "resources"
    internal_res = target_dir / "_internal" / "resources"
    if internal_res.exists() and not res_dir.exists():
        try:
            shutil.copytree(internal_res, res_dir)
        except Exception:
            pass
    elif not res_dir.exists():
        res_dir.mkdir(parents=True, exist_ok=True)

    icon_candidates = [
        target_dir / "resources" / "icon.ico",
        target_dir / "_internal" / "resources" / "icon.ico",
        target_dir / "resources" / "icon_32.png",
        target_dir / "_internal" / "resources" / "icon_32.png",
        app_exe,
    ]
    icon_file = next((p for p in icon_candidates if p.exists()), app_exe)

    if progress_callback: progress_callback(85, "正在创建桌面与开始菜单快捷方式...")
    if create_desktop:
        desktop = Path.home() / "Desktop"
        create_shortcut(app_exe, desktop / f"{APP_NAME}.lnk", icon_file, f"{APP_NAME} 桌面控制中心")

    if create_start_menu:
        start_menu = Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        create_shortcut(app_exe, start_menu / f"{APP_NAME}.lnk", icon_file, f"{APP_NAME} 桌面控制中心")

    if progress_callback: progress_callback(95, "正在配置系统卸载入口...")
    register_uninstall(target_dir)
    write_uninstaller(target_dir)

    if progress_callback: progress_callback(100, "安装完成！")
    return True, "安装成功"


def run_gui_installer():
    """现代化 Tkinter 原生安装向导界面"""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                import ctypes
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog

    root = tk.Tk()
    root.title(f"{APP_NAME} 安装向导")
    root.geometry("560x430")
    root.minsize(540, 420)
    root.resizable(False, False)

    root.update_idletasks()
    x = (root.winfo_screenwidth() - 560) // 2
    y = (root.winfo_screenheight() - 430) // 2
    root.geometry(f"+{x}+{y}")

    icon_path = get_resource_path("icon.ico")
    if icon_path.exists():
        try:
            root.iconbitmap(str(icon_path))
        except Exception:
            pass

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("TButton", font=("Microsoft YaHei", 9), padding=(10, 5))

    header_frame = tk.Frame(root, bg="#1e293b", height=74)
    header_frame.pack(fill=tk.X, side=tk.TOP)
    header_frame.pack_propagate(False)

    lbl_title = tk.Label(header_frame, text=f"{APP_NAME} v{APP_VERSION}", font=("Microsoft YaHei", 14, "bold"), fg="#ffffff", bg="#1e293b")
    lbl_title.pack(anchor="w", padx=22, pady=(14, 2))
    lbl_sub = tk.Label(header_frame, text="极速桌面控制中心 · 原生 0.017s 秒开极速体验", font=("Microsoft YaHei", 9), fg="#94a3b8", bg="#1e293b")
    lbl_sub.pack(anchor="w", padx=22)

    # 1. 底部操作栏优先置底排布，确保在任何屏幕缩放与高 DPI 下均保持完整高度不被压缩截断
    btn_frame = tk.Frame(root, padx=22, pady=14, bg="#f8fafc", bd=1, relief=tk.RIDGE)
    btn_frame.pack(fill=tk.X, side=tk.BOTTOM)

    def do_install():
        entry_path.config(state="disabled")
        btn_browse.config(state="disabled")
        chk_desktop.config(state="disabled")
        chk_start.config(state="disabled")
        chk_launch.config(state="disabled")
        btn_install.config(state="disabled", bg="#93c5fd", cursor="wait")
        btn_cancel.config(state="disabled", bg="#f1f5f9", fg="#94a3b8")

        import threading
        def _worker():
            def _cb(pct, text):
                progress_var.set(pct)
                status_var.set(text)
                root.update_idletasks()

            target = Path(path_var.get().strip())
            ok, msg = perform_installation(target, var_desktop.get(), var_startmenu.get(), progress_callback=_cb)
            if ok:
                btn_install.config(text="完成并退出", state="normal", bg="#10b981", activebackground="#059669", cursor="hand2", command=root.destroy)
                if var_launch.get():
                    app_exe = target / EXE_NAME
                    if app_exe.exists():
                        subprocess.Popen([str(app_exe)], cwd=str(target))
                messagebox.showinfo("安装成功", f"{APP_NAME} 已成功安装到您的电脑！\n\n您现在可以通过桌面快捷方式享受 0.017 秒秒开体验。")
                root.destroy()
            else:
                messagebox.showerror("安装失败", f"安装过程出错: {msg}")
                btn_cancel.config(state="normal", bg="#e2e8f0", fg="#334155", cursor="hand2")

        threading.Thread(target=_worker, daemon=True).start()

    btn_cancel = tk.Button(
        btn_frame,
        text="取消",
        command=root.destroy,
        bg="#e2e8f0",
        fg="#334155",
        activebackground="#cbd5e1",
        activeforeground="#0f172a",
        relief=tk.FLAT,
        bd=0,
        padx=16,
        pady=7,
        font=("Microsoft YaHei", 9),
        cursor="hand2"
    )
    btn_cancel.pack(side=tk.RIGHT, padx=(10, 0))

    btn_install = tk.Button(
        btn_frame,
        text="立即安装 (秒级部署)",
        command=do_install,
        bg="#2563eb",
        fg="#ffffff",
        activebackground="#1d4ed8",
        activeforeground="#ffffff",
        relief=tk.FLAT,
        bd=0,
        padx=18,
        pady=7,
        font=("Microsoft YaHei", 9, "bold"),
        cursor="hand2"
    )
    btn_install.pack(side=tk.RIGHT)

    # 2. 中间主要配置区
    content_frame = tk.Frame(root, padx=25, pady=16)
    content_frame.pack(fill=tk.BOTH, expand=True)

    tk.Label(content_frame, text="安装目标文件夹:", font=("Microsoft YaHei", 9, "bold"), fg="#334155").pack(anchor="w")
    path_row = tk.Frame(content_frame)
    path_row.pack(fill=tk.X, pady=(6, 12))

    # 自动识别并预填之前安装过的历史目录
    saved_install_dir = get_previous_install_dir()
    path_var = tk.StringVar(value=str(saved_install_dir))
    entry_path = ttk.Entry(path_row, textvariable=path_var, font=("Microsoft YaHei", 9))
    entry_path.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

    def choose_dir():
        d = filedialog.askdirectory(initialdir=path_var.get())
        if d:
            path_var.set(d)

    btn_browse = ttk.Button(path_row, text="浏览...", width=8, command=choose_dir)
    btn_browse.pack(side=tk.RIGHT)

    opt_frame = tk.Frame(content_frame)
    opt_frame.pack(fill=tk.X, pady=(0, 10))

    var_desktop = tk.BooleanVar(value=True)
    var_startmenu = tk.BooleanVar(value=True)
    var_launch = tk.BooleanVar(value=True)

    chk_desktop = tk.Checkbutton(opt_frame, text="创建桌面快捷方式 (推荐)", variable=var_desktop, font=("Microsoft YaHei", 9), fg="#334155")
    chk_desktop.pack(anchor="w", pady=1)
    chk_start = tk.Checkbutton(opt_frame, text="创建开始菜单项", variable=var_startmenu, font=("Microsoft YaHei", 9), fg="#334155")
    chk_start.pack(anchor="w", pady=1)
    chk_launch = tk.Checkbutton(opt_frame, text="安装完成后立即启动", variable=var_launch, font=("Microsoft YaHei", 9), fg="#334155")
    chk_launch.pack(anchor="w", pady=1)

    progress_var = tk.DoubleVar(value=0)
    progress_bar = ttk.Progressbar(content_frame, variable=progress_var, maximum=100)
    progress_bar.pack(fill=tk.X, pady=(8, 4))

    status_var = tk.StringVar(value="准备就绪，点击「立即安装」开始部署")
    lbl_status = tk.Label(content_frame, textvariable=status_var, font=("Microsoft YaHei", 8), fg="#64748b")
    lbl_status.pack(anchor="w")

    root.mainloop()


def main():
    if "/S" in sys.argv or "/s" in sys.argv or "/SILENT" in sys.argv:
        target = DEFAULT_INSTALL_DIR
        for arg in sys.argv:
            if arg.startswith("/D="):
                target = Path(arg.split("=", 1)[1])
        ok, msg = perform_installation(target, create_desktop=True, create_start_menu=True)
        sys.exit(0 if ok else 1)
    else:
        run_gui_installer()


if __name__ == "__main__":
    main()
