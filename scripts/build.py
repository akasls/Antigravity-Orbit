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

    # 终止可能仍在后台驻留的旧版 Orbit 进程，避免 Windows 文件锁定 PermissionError
    if system == "windows":
        subprocess.run("taskkill /F /IM Antigravity-Orbit.exe /IM Antigravity-Orbit-Portable-x64.exe 2>nul", shell=True, capture_output=True)

    # 路径分隔符适配 (Windows 用分号 ;, Unix 用冒号 :)
    sep = ";" if system == "windows" else ":"

    # 严格排除无用重型第三方科学、Qt与测试库，将体积与解压启动时间压缩至极限
    excludes = [
        "--exclude-module", "PyQt6",
        "--exclude-module", "PyQt5",
        "--exclude-module", "PySide6",
        "--exclude-module", "PySide2",
        "--exclude-module", "qtpy",
        "--exclude-module", "tkinter",
        "--exclude-module", "_tkinter",
        "--exclude-module", "numpy",
        "--exclude-module", "scipy",
        "--exclude-module", "matplotlib",
        "--exclude-module", "pandas",
        "--exclude-module", "playwright",
        "--exclude-module", "pytest",
        "--exclude-module", "unittest",
        "--exclude-module", "pydoc",
        "--exclude-module", "doctest",
        "--exclude-module", "test",
        "--exclude-module", "IPython",
        "--exclude-module", "jedi",
    ]

    # 构建基础参数
    base_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        f"--add-data=localization{sep}localization",
        f"--add-data=resources{sep}resources",
        f"--add-data=core/web{sep}core/web",
        f"--add-data=config.example.json{sep}.",
    ] + excludes

    # 图标适配
    icon_win = PROJECT_ROOT / "resources" / "icon.ico"
    icon_mac = PROJECT_ROOT / "resources" / "icon.icns"

    if system == "windows":
        # 1. 优先构建 Onedir 极速目录版 (解压后 0.15s 秒开，彻底摆脱临时目录解压和杀软拦截)
        print("\n>>> [1/2] 正在构建 Windows 秒开免解压极速版 (Onedir)...")
        cmd_dir = base_cmd + [
            "--onedir",
            "--name", "Antigravity-Orbit",
            "--icon", str(icon_win),
            "main.py"
        ]
        ret = subprocess.run(cmd_dir, cwd=str(PROJECT_ROOT))
        if ret.returncode != 0:
            print(f"[错误] Onedir 打包失败 (退出码: {ret.returncode})")
            sys.exit(ret.returncode)

        app_dir = DIST_DIR / "Antigravity-Orbit"
        if app_dir.exists():
            zip_name = DIST_DIR / "Antigravity-Orbit-Windows-x64"
            print(f"[ARCHIVE] 正在压缩 Onedir 秒开目录包: {zip_name}.zip ...")
            # 压缩包含 Antigravity-Orbit 根目录的结构
            shutil.make_archive(str(zip_name), 'zip', str(DIST_DIR), "Antigravity-Orbit")
            print(f"[OK] 极速秒开版压缩包就绪: {zip_name}.zip")

        # 2. 构建 Onefile 单文件独立便携版
        print("\n>>> [2/2] 正在构建 Windows 单文件便携版 (Onefile)...")
        cmd_file = base_cmd + [
            "--onefile",
            "--name", "Antigravity-Orbit-Portable-x64",
            "--icon", str(icon_win),
            "main.py"
        ]
        ret2 = subprocess.run(cmd_file, cwd=str(PROJECT_ROOT))
        if ret2.returncode != 0:
            print(f"[错误] Onefile 单文件打包失败 (退出码: {ret2.returncode})")
            sys.exit(ret2.returncode)

        portable_exe = DIST_DIR / "Antigravity-Orbit-Portable-x64.exe"
        print(f"[OK] 单文件便携版就绪: {portable_exe}")

    elif system == "darwin":
        # macOS: 打包为 .app 应用包
        cmd_mac = base_cmd + [
            "--onedir",
            "--name", "Antigravity-Orbit",
            "--osx-bundle-identifier", "com.antigravity.orbit",
        ]
        if icon_mac.exists():
            cmd_mac.extend(["--icon", str(icon_mac)])
        cmd_mac.append("main.py")

        ret = subprocess.run(cmd_mac, cwd=str(PROJECT_ROOT))
        if ret.returncode != 0:
            print(f"[错误] macOS 打包失败 (退出码: {ret.returncode})")
            sys.exit(ret.returncode)

        app_path = DIST_DIR / "Antigravity-Orbit.app"
        if app_path.exists():
            zip_name = DIST_DIR / "Antigravity-Orbit-macOS"
            print(f"[ARCHIVE] 正在打包为 Zip: {zip_name}.zip ...")
            subprocess.run(["zip", "-r", "-y", f"{zip_name}.zip", "Antigravity-Orbit.app"], cwd=str(DIST_DIR))
            print(f"[OK] macOS .app 应用包就绪: {app_path}")
            print(f"[OK] 压缩包就绪: {zip_name}.zip")

    print("\n==================================================")
    print("[SUCCESS] Antigravity Orbit 全部打包构建完成！产物位于 dist/ 目录。")
    print("==================================================")


if __name__ == "__main__":
    build()
