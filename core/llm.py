"""OpenAI 兼容接口的最小实现，仅依赖标准库。"""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request


class LLMError(RuntimeError):
    """调用模型失败，message 可直接展示给用户。"""


_HINTS = {
    400: "请求参数有误",
    401: "API Key 无效或已过期",
    402: "账户余额不足",
    403: "无权访问该模型",
    404: "接口地址或模型名不正确",
    422: "请求参数有误",
    429: "请求过于频繁，请稍后再试",
    500: "模型服务内部错误",
    503: "模型服务暂时不可用",
}


def chat(cfg: dict, system: str, user: str, temperature: float | None = None,
         timeout: int | None = None) -> str:
    llm = cfg.get("llm") or {}
    key = (llm.get("api_key") or "").strip()
    if not key:
        raise LLMError("未配置 API Key：点右上角「设置」填入 DeepSeek 或其他兼容服务的 Key")

    base = (llm.get("base_url") or "https://api.deepseek.com").rstrip("/")
    url = base + "/chat/completions"
    body = {
        "model": llm.get("model") or "deepseek-chat",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": llm.get("temperature", 0.2) if temperature is None else temperature,
        "stream": False,
    }
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout or llm.get("timeout", 60)) as resp:
            raw = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", "replace")[:300]
        except Exception:  # noqa: BLE001
            pass
        hint = _HINTS.get(exc.code, "接口返回错误")
        raise LLMError(f"{hint}（HTTP {exc.code}）{detail}") from exc
    except (urllib.error.URLError, socket.timeout, TimeoutError) as exc:
        raise LLMError(f"网络请求失败：{exc}；请检查网络、代理或 base_url 设置") from exc

    try:
        payload = json.loads(raw)
        return payload["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"模型返回格式异常：{raw[:200]}") from exc
