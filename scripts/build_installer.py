# -*- coding: utf-8 -*-
"""
Antigravity Orbit 安装程序自动打包器 (Windows Setup Builder)
支持优先检测 Inno Setup，若无则自动使用原生内置模板生成独立 Setup.exe 安装包。
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = PROJECT_ROOT / "dist"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
RESOURCES_DIR = PROJECT_ROOT / "resources"


def find_inno_compiler() -> Path | None:
    """搜索系统中的 Inno Setup 编译器 (ISCC.exe)"""
    iscc = shutil.which("iscc") or shutil.which("ISCC")
    if iscc:
        return Path(iscc)

    candidates = [
        Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def build_with_inno(iscc_path: Path) -> bool:
    """通过 Inno Setup 编译标准安装包"""
    print(f"[Inno Setup] 检测到 Inno 编译器: {iscc_path}")
    iss_file = SCRIPTS_DIR / "installer.iss"
    if not iss_file.exists():
        print(f"[错误] 未找到 Inno 脚本: {iss_file}")
        return False

    cmd = [str(iscc_path), str(iss_file)]
    res = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    return res.returncode == 0


def build_with_native_template() -> bool:
    """使用内置原生独立安装程序生成器封装 Setup.exe"""
    print("[Native Setup] 正在使用内置原生安装程序模板封装 Setup.exe...")

    payload_zip = DIST_DIR / "Antigravity-Orbit-Windows-x64.zip"
    if not payload_zip.exists():
        print(f"[错误] 未找到免解压压缩包: {payload_zip}")
        return False

    icon_ico = RESOURCES_DIR / "icon.ico"
    installer_script = SCRIPTS_DIR / "installer_template.py"

    # 将 payload_zip 与 icon 打包为单文件安装器
    sep = ";" if sys.platform == "win32" else ":"
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name", "Antigravity-Orbit-Setup",
        f"--add-data={payload_zip}{sep}.",
        f"--add-data={icon_ico}{sep}.",
    ]
    if icon_ico.exists():
        cmd.extend(["--icon", str(icon_ico)])

    cmd.append(str(installer_script))

    res = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    if res.returncode == 0:
        # 重命名临时文件名并移动至 dist/ 根目录
        setup_exe = DIST_DIR / "Antigravity-Orbit-Setup.exe"
        if setup_exe.exists():
            print(f"[OK] 原生安装包构建成功: {setup_exe}")
            return True
    return False


def build_installer():
    print("==================================================")
    print("[BUILD] 开始构建 Antigravity Orbit Windows 安装包")
    print("==================================================")

    inno_path = find_inno_compiler()
    if inno_path:
        ok = build_with_inno(inno_path)
        if ok:
            print("[SUCCESS] Inno Setup 安装包已成功输出至 dist/Antigravity-Orbit-Setup.exe")
            return True

    # 若未安装 Inno 或编译失败，回退为内置原生安装程序
    ok = build_with_native_template()
    if ok:
        print("[SUCCESS] 原生安装包已成功输出至 dist/Antigravity-Orbit-Setup.exe")
        return True
    else:
        print("[FAIL] 安装包构建失败！")
        return False


if __name__ == "__main__":
    success = build_installer()
    sys.exit(0 if success else 1)
