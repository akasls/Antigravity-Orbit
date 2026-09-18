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

:: 执行模式选择
if not "%~1"=="" (
    %PY_CMD% "%~dp0main.py" %*
    echo.
    pause
    exit /b 0
)

echo ========================================================
echo   🌌 Antigravity Orbit - 综合管理与配置
echo ========================================================
echo.
echo   [1] 启动【桌面可视化控制中心】 (Native GUI 桌面软件, 推荐)
echo   [2] 运行【命令行交互式配置向导】 (Console CLI 向导)
echo   [0] 退出
echo.
set /p "CHOICE=请选择运行模式 [1/2/0, 默认 1]: "

if "%CHOICE%"=="" set "CHOICE=1"
if "%CHOICE%"=="1" (
    where pythonw >nul 2>nul
    if %errorlevel% equ 0 (
        start "" pythonw "%~dp0main.py" gui
    ) else (
        start "" %PY_CMD% "%~dp0main.py" gui
    )
    exit /b 0
)
if "%CHOICE%"=="2" (
    %PY_CMD% "%~dp0main.py" setup
    echo.
    pause
    exit /b 0
)
exit /b 0



