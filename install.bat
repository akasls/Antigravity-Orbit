@echo off
chcp 65001 >nul
title Antigravity Orbit 安装向导

set "DIR=%~dp0"
cd /d "%DIR%"

echo ========================================================
echo   🌌 Antigravity Orbit - 安装向导与管理中心
echo ========================================================
echo.

:: 1. 若已存在编译好的 Setup.exe 安装程序，直接唤起
if exist "%DIR%dist\Antigravity-Orbit-Setup.exe" (
    echo [发现安装包] 正在启动 Antigravity Orbit 安装向导...
    start "" "%DIR%dist\Antigravity-Orbit-Setup.exe"
    exit /b 0
)

:: 2. 源码环境或已构建目录模式
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未在系统 PATH 中检测到 Python 环境，无法执行向导。
    pause
    exit /b 1
)

echo   [1] 立即安装到电脑 (一键部署至应用目录、自动生成桌面与开始菜单快捷方式)
echo   [2] 启动桌面控制中心 (0.017秒极速秒开模式)
echo   [3] 卸载当前已安装版本
echo   [0] 退出
echo.
set /p "CHOICE=请选择操作 [1/2/3/0, 默认 1]: "
if "%CHOICE%"=="" set "CHOICE=1"

if "%CHOICE%"=="1" (
    python "%DIR%scripts\installer_template.py"
    exit /b 0
)
if "%CHOICE%"=="2" (
    call "%DIR%gui.bat"
    exit /b 0
)
if "%CHOICE%"=="3" (
    set "UNINST=%LOCALAPPDATA%\Programs\Antigravity-Orbit\uninstall.bat"
    if exist "%UNINST%" (
        call "%UNINST%"
    ) else (
        echo [提示] 未在系统应用目录检测到已安装的 Antigravity Orbit。
    )
    pause
    exit /b 0
)
exit /b 0
