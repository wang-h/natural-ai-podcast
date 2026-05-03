"""OpenAI-compatible LLM API calls with retry logic."""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request


def call_llm_openai(api_key: str, base_url: str, model: str, system: str, user: str,
                    temperature: float = 0.55) -> str:
    base = base_url.rstrip("/")
    url = f"{base}/chat/completions" if "/v1" in base else f"{base}/v1/chat/completions"
    body = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM(openai) HTTP {exc.code}: {detail}") from exc
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    if not content:
        raise RuntimeError("LLM(openai) returned no content")
    content = re.sub(r"<think\b[^>]*>.*?</think\s*>", "", content, flags=re.DOTALL | re.IGNORECASE).strip()
    return content


def call_llm(system: str, user: str, model: str, api_key: str, base_url: str,
             temperature: float = 0.55) -> str:
    for attempt in range(4):
        try:
            return call_llm_openai(api_key, base_url, model, system, user, temperature)
        except RuntimeError as exc:
            msg = str(exc).lower()
            if any(k in msg for k in ("rate limit", "rpm", "429")):
                time.sleep(15 * (attempt + 1))
                continue
            if any(k in msg for k in ("502", "503", "529")):
                time.sleep(5 * (attempt + 1))
                continue
            raise
    raise RuntimeError("LLM request failed after 4 retries")
