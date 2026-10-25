#!/bin/sh
# Englearn 在 Linux / macOS 上的启动脚本（网页模式：无全局热键、无悬浮窗）。
# Windows 用户请直接双击 start.cmd。
set -eu
cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "未找到 Python 3.10+，请先安装。" >&2
    exit 1
fi

exec "$PY" app.py --no-popup "$@"
