"""开机自启管理（Windows：写入 HKCU 的 Run 键，无需管理员权限）。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VBS = ROOT / "scripts" / "start-hidden.vbs"

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "Englearn"


def supported() -> bool:
    return sys.platform == "win32"


def _command() -> str:
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    wscript = Path(system_root) / "System32" / "wscript.exe"
    return f'"{wscript}" "{VBS}"'


def is_enabled() -> bool:
    if not supported():
        return False
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, VALUE_NAME)
            return bool(str(value).strip())
    except FileNotFoundError:
        return False
    except OSError:
        return False


def enable() -> None:
    if not supported():
        raise RuntimeError("仅支持 Windows")
    if not VBS.exists():
        raise RuntimeError(f"缺少启动脚本：{VBS}")
    import winreg

    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, _command())


def disable() -> None:
    if not supported():
        return
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, VALUE_NAME)
    except FileNotFoundError:
        pass


def status() -> dict:
    return {
        "supported": supported(),
        "enabled": is_enabled(),
        "command": _command() if supported() else "",
    }
