#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "[错误] 未检测到 Python 环境，请先安装 Python 3.8+！"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "[提示] 未检测到 Node.js 环境，若需进行客户端界面汉化，建议安装 Node.js (https://nodejs.org)。"
    echo ""
fi

if [ -z "$1" ]; then
    $PYTHON_CMD "$SCRIPT_DIR/main.py" setup
else
    $PYTHON_CMD "$SCRIPT_DIR/main.py" "$@"
fi


