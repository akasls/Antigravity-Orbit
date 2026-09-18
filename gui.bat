@echo off
chcp 65001 >nul
title Antigravity Orbit 桌面控制中心

set "DIR=%~dp0"
cd /d "%DIR%"

:: 1. 优先唤起免解压极速版 (0.15秒闪电启动)
if exist "%DIR%dist\Antigravity-Orbit\Antigravity-Orbit.exe" (
    start "" "%DIR%dist\Antigravity-Orbit\Antigravity-Orbit.exe" %*
    exit /b 0
)

:: 2. 其次唤起单文件便携版
if exist "%DIR%dist\Antigravity-Orbit-Portable-x64.exe" (
    start "" "%DIR%dist\Antigravity-Orbit-Portable-x64.exe" %*
    exit /b 0
)

:: 3. 源码环境回退：优先寻找 pythonw.exe 避免控制台常驻黑框，若无则回退为 python.exe
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
