#!/usr/bin/env python3
"""
Antigravity Orbit 跨平台自动打包脚本
支持 Windows 单文件 (.exe) 与 macOS 应用包 (.app / .dmg / .zip)
"""

import os
import sys

# 适配 Windows 控制台编码，防止 GBK 终端打印特殊字符引发 UnicodeEncodeError
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import shutil
import platform
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"


def check_pyinstaller():
    try:
        import PyInstaller
        return True
    except ImportError:
        pass
    if shutil.which("pyinstaller"):
        return True
    return False


def build():
    system = platform.system().lower()
    print("==================================================")
    print(f"[BUILD] 开始打包 Antigravity Orbit (操作系统: {platform.system()})")
    print("==================================================")

    if not check_pyinstaller():
        print("[提示] 检测到当前环境未安装 PyInstaller，正在自动安装...")
        res = subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], cwd=str(PROJECT_ROOT))
        if res.returncode != 0:
            print("[错误] PyInstaller 安装失败，请手动运行: pip install pyinstaller")
            sys.exit(1)

    # 路径分隔符适配 (Windows 用分号 ;, Unix 用冒号 :)
    sep = ";" if system == "windows" else ":"

    # 构建基础参数
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name", "Antigravity-Orbit",
        f"--add-data=localization{sep}localization",
        f"--add-data=resources{sep}resources",
        f"--add-data=config.example.json{sep}.",
    ]

    # 图标适配
    icon_win = PROJECT_ROOT / "resources" / "icon.ico"
    icon_mac = PROJECT_ROOT / "resources" / "icon.icns"

    if system == "windows":
        # Windows: 打包为单文件 exe
        cmd.append("--onefile")
        if icon_win.exists():
            cmd.extend(["--icon", str(icon_win)])
    elif system == "darwin":
        # macOS: 打包为 .app 应用包
        cmd.append("--onedir")
        if icon_mac.exists():
            cmd.extend(["--icon", str(icon_mac)])
        # 增加 Info.plist 基础元数据
        cmd.extend([
            "--osx-bundle-identifier", "com.antigravity.orbit",
        ])
    else:
        # Linux
        cmd.append("--onefile")

    cmd.append("main.py")

    print(f"\n[执行命令] {' '.join(cmd)}\n")
    ret = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    if ret.returncode != 0:
        print(f"\n[错误] PyInstaller 编译失败 (退出码: {ret.returncode})")
        sys.exit(ret.returncode)

    print("\n==================================================")
    print("[ARCHIVE] 编译完成，正在处理发布归档产物...")

    if system == "windows":
        exe_file = DIST_DIR / "Antigravity-Orbit.exe"
        if exe_file.exists():
            zip_name = DIST_DIR / "Antigravity-Orbit-Windows-x64"
            print(f"[ARCHIVE] 正在打包为 Zip: {zip_name}.zip ...")
            shutil.make_archive(str(zip_name), 'zip', str(DIST_DIR), "Antigravity-Orbit.exe")
            print(f"[OK] Windows 客户端产物就绪: {exe_file}")
            print(f"[OK] 压缩包就绪: {zip_name}.zip")

    elif system == "darwin":
        app_path = DIST_DIR / "Antigravity-Orbit.app"
        if app_path.exists():
            zip_name = DIST_DIR / "Antigravity-Orbit-macOS"
            print(f"[ARCHIVE] 正在打包为 Zip: {zip_name}.zip ...")
            subprocess.run(["zip", "-r", "-y", f"{zip_name}.zip", "Antigravity-Orbit.app"], cwd=str(DIST_DIR))
            print(f"[OK] macOS .app 应用包就绪: {app_path}")
            print(f"[OK] 压缩包就绪: {zip_name}.zip")

    print("==================================================")
    print("[SUCCESS] Antigravity Orbit 全部打包任务完成！产物位于 dist/ 目录。")
    print("==================================================")


if __name__ == "__main__":
    build()
