@echo off
chcp 65001 >nul
title Antigravity Orbit 桌面控制中心

set "DIR=%~dp0"
cd /d "%DIR%"

:: 优先寻找 pythonw.exe 避免控制台常驻黑框，若无则回退为 python.exe
where pythonw >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    start "" pythonw "%DIR%main.py" gui %*
) else (
    where python >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        start "" python "%DIR%main.py" gui %*
    ) else (
        echo [错误] 未在系统 PATH 中检测到 Python 环境，请先安装 Python 3.8+。
        pause
    )
)
exit /b 0
