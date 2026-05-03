"""MiniMax TTS API client."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

from .text_utils import SPEECH_TAG_RE, PAUSE_RE


def minimax_tts(api_key: str, base_url: str, model: str, text: str, voice_id: str,
                emotion: str = "fluent", fallback_emotion: str = "fluent") -> bytes:
    supports_tags = model in ("speech-2.8-hd", "speech-2.8-turbo")
    clean_text = text
    if not supports_tags:
        clean_text = SPEECH_TAG_RE.sub("", text)
        clean_text = PAUSE_RE.sub("", clean_text)

    url = base_url.rstrip("/") + "/v1/t2a_v2"

    candidates: list[str] = []
    for emo in (emotion, fallback_emotion, ""):
        emo = (emo or "").strip().lower()
        if emo not in candidates:
            candidates.append(emo)

    last_error = ""
    for emo in candidates:
        body = {
            "model": model, "text": clean_text, "stream": False,
            "language_boost": "Chinese", "output_format": "hex",
            "voice_setting": {
                "voice_id": voice_id,
                "speed": 1,
                "vol": 1,
                "pitch": 0,
                **({"emotion": emo} if emo else {}),
            },
            "audio_setting": {"sample_rate": 32000, "bitrate": 128000, "format": "mp3", "channel": 1},
            "aigc_watermark": False,
        }

        for attempt in range(6):
            req = urllib.request.Request(
                url, data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace").lower()
                last_error = f"MiniMax TTS HTTP {exc.code}: {detail[:300]}"
                if exc.code in (429, 502, 503, 529) or any(k in detail for k in ("rate limit", "rpm", "too many")):
                    wait = min(20, 3 * (2 ** attempt))
                    time.sleep(wait)
                    continue
                if emo and any(k in detail for k in ("emotion", "voice_setting", "invalid", "unsupported", "not support")):
                    break  # try fallback emotion
                raise RuntimeError(last_error) from exc

            status = payload.get("base_resp", {}).get("status_code")
            if status not in (None, 0):
                msg = payload.get('base_resp', {}).get('status_msg') or str(status)
                last_error = f"MiniMax TTS failed: {msg}"
                msg_l = str(msg).lower()
                if any(k in msg_l for k in ("rate", "limit", "rpm", "too many", "frequency")):
                    wait = min(20, 3 * (2 ** attempt))
                    time.sleep(wait)
                    continue
                if emo and any(k in msg_l for k in ("emotion", "voice_setting", "invalid", "unsupported", "not support")):
                    break  # try fallback emotion
                raise RuntimeError(last_error)
            audio = payload.get("data", {}).get("audio") or payload.get("audio_file")
            if not audio:
                last_error = "MiniMax returned no audio"
                raise RuntimeError(last_error)
            return bytes.fromhex(audio.strip())

    raise RuntimeError(last_error or "MiniMax TTS failed after retries")
