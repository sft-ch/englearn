"""配置读写：config.json 位于项目根目录，首次运行自动生成。"""

from __future__ import annotations

import copy
import json
import os
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# 允许用 ENGL_CONFIG 指向另一份配置（多实例、演示、测试时用）
CONFIG_PATH = Path(os.environ.get("ENGL_CONFIG") or (ROOT / "config.json"))

DEFAULTS = {
    "host": "127.0.0.1",
    "port": 8765,
    "hotkey": "alt+d",
    "clipboard_watch": False,
    "select_popup": True,
    "max_chars": 4000,
    "mock": False,
    "llm": {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "api_key": "",
        "timeout": 60,
        "temperature": 0.2,
    },
}

_lock = threading.Lock()


def _merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def load() -> dict:
    """读取配置，缺失字段用默认值补齐。"""
    data = {}
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
    if not isinstance(data, dict):
        data = {}
    with _lock:
        return _merge(DEFAULTS, data)


def save(cfg: dict) -> None:
    with _lock:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )


def public_view(cfg: dict) -> dict:
    """给前端看的配置：隐藏 API Key，只暴露是否已配置。"""
    view = copy.deepcopy(cfg)
    llm = view.setdefault("llm", {})
    key = (llm.get("api_key") or "").strip()
    llm["api_key"] = ""
    llm["has_key"] = bool(key)
    return view
