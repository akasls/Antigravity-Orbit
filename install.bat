@echo off
chcp 65001 >nul
title Antigravity 综合配置向导

:: 检查 Python 环境
where python >nul 2>nul
if %errorlevel% equ 0 (
    set "PY_CMD=python"
    goto CHECK_NODE
)

where py >nul 2>nul
if %errorlevel% equ 0 (
    set "PY_CMD=py"
    goto CHECK_NODE
)

echo ========================================================
echo [错误] 未检测到 Python 环境！
echo.
echo 请先安装 Python 3.8 或以上版本，并勾选 Add Python to PATH！
echo 官方下载地址: https://www.python.org/downloads/
echo ========================================================
echo.
pause
exit /b 1

:CHECK_NODE
:: 检查 Node.js 环境 (客户端界面汉化需要 Node.js)
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [提示] 未检测到 Node.js 环境。若需进行客户端界面汉化，请访问 https://nodejs.org 安装。
    echo.
)

:: 执行主程序配置向导 (默认直接进入顺序向导: 先问汉化，再问通知)
if "%~1"=="" (
    %PY_CMD% "%~dp0main.py" setup
) else (
    %PY_CMD% "%~dp0main.py" %*
)

echo.
pause



