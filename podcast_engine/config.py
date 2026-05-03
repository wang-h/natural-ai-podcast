"""Constants, paths, environment helpers, and config resolvers."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ENV = PROJECT_DIR / ".env"
SAMPLES_DIR = Path(os.environ.get("PODCAST_SAMPLES_DIR", str(PROJECT_DIR.parent / "podcast-edge-samples")))

INTRO_FILE = PROJECT_DIR / "assets" / "intro.mp3"
OUTRO_FILE = PROJECT_DIR / "assets" / "outro.mp3"

_DEFAULT_VOICE_A = "Chinese (Mandarin)_Southern_Young_Man"
_DEFAULT_VOICE_B = "Chinese (Mandarin)_HK_Flight_Attendant"


def _build_voice_map(env: dict[str, str] | None = None) -> dict[str, str]:
    if env is None:
        env = read_env()
    return {
        "林深": env.get("HOST_A_VOICE_ID") or _DEFAULT_VOICE_A,
        "若水": env.get("HOST_B_VOICE_ID") or _DEFAULT_VOICE_B,
    }


# ---------------------------------------------------------------------------
# environment
# ---------------------------------------------------------------------------

def read_env(path: Path = DEFAULT_ENV) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        values[key.strip()] = value
    return values


# ---------------------------------------------------------------------------
# config resolvers
# ---------------------------------------------------------------------------

def resolve_llm_config(env: dict[str, str] | None = None, *,
                       api_key: str | None = None,
                       base_url: str | None = None,
                       model: str | None = None) -> dict[str, str]:
    """Resolve LLM config from env + overrides. Returns {api_key, base_url, model}."""
    if env is None:
        env = read_env()
    key = api_key or env.get("MINIMAX_API_KEY") or ""
    base = base_url or env.get("MINIMAX_BASE_URL") or "https://api.minimaxi.com/v1"
    m = model or env.get("MINIMAX_MODEL") or "MiniMax-M2.7"
    return {"api_key": key, "base_url": base, "model": m}


def resolve_tts_config(env: dict[str, str] | None = None, *,
                       api_key: str | None = None,
                       base_url: str | None = None,
                       model: str | None = None) -> dict[str, str]:
    """Resolve TTS config from env + overrides."""
    if env is None:
        env = read_env()
    key = api_key or env.get("MINIMAX_TTS_API_KEY") or env.get("MINIMAX_API_KEY") or ""
    base = base_url or env.get("MINIMAX_TTS_BASE_URL") or "https://api.minimaxi.com"
    m = model or env.get("MINIMAX_TTS_MODEL") or "speech-2.8-hd"
    return {"api_key": key, "base_url": base, "model": m}
