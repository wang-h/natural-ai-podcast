"""Text parsing, emotion/timing hint extraction, and overlap inference."""

from __future__ import annotations

import re

from .config import read_env

SPEECH_TAG_NAMES = [
    "laughs", "chuckle", "coughs", "clear-throat", "groans",
    "breath", "pant", "inhale", "exhale", "gasps", "sniffs",
    "sighs", "snorts", "burps", "lip-smacking", "humming",
    "hissing", "emm", "sneezes",
]
SPEECH_TAG_RE = re.compile(r"\((?:{})\)".format("|".join(SPEECH_TAG_NAMES)), re.I)
PAUSE_RE = re.compile(r"<#\d+(?:\.\d+)?#>")

# Optional non-spoken inline hint for manual overrides.
EMOTION_HINT_RE = re.compile(r"\[\[emotion=([a-zA-Z_-]+)\]\]", re.I)

# Non-spoken timing hints for natural turn-taking.
TIMING_HINT_RE = re.compile(r"\[\[(interrupt|overlap|gap)=(-?\d{1,4})\]\]", re.I)

_DEFAULT_ALLOWED_TTS_EMOTIONS = {
    "fluent", "happy", "sad", "angry", "fearful", "disgusted", "surprised", "neutral"
}


def _allowed_tts_emotions(env: dict[str, str] | None = None) -> set[str]:
    if env is None:
        env = read_env()
    raw = env.get("MINIMAX_TTS_ALLOWED_EMOTIONS", "")
    if not raw.strip():
        return set(_DEFAULT_ALLOWED_TTS_EMOTIONS)
    return {x.strip().lower() for x in raw.split(",") if x.strip()}


def _extract_explicit_emotion(text: str) -> tuple[str | None, str]:
    """Return (emotion_hint, cleaned_text). Hints are non-spoken."""
    found = EMOTION_HINT_RE.findall(text)
    cleaned = EMOTION_HINT_RE.sub("", text).strip()
    return (found[0].lower() if found else None), cleaned


def _extract_timing_hints(text: str) -> tuple[dict[str, int], str]:
    """Return ({overlap_ms, gap_ms}, cleaned_text). Timing hints are non-spoken."""
    hints: dict[str, int] = {"overlap_ms": 0, "gap_ms": 0}

    def repl(match: re.Match[str]) -> str:
        kind = match.group(1).lower()
        value = int(match.group(2))
        value = max(-1000, min(1200, value))
        if kind in ("interrupt", "overlap"):
            hints["overlap_ms"] = max(0, value)
        elif kind == "gap":
            hints["gap_ms"] = value
        return ""

    cleaned = TIMING_HINT_RE.sub(repl, text).strip()
    return hints, cleaned


def _remove_nonspoken_hints(text: str) -> str:
    """Remove all non-spoken renderer hints from text."""
    _, text = _extract_timing_hints(text)
    _, text = _extract_explicit_emotion(text)
    return text.strip()


def _is_fixed_opening_or_closing(index: int, total: int) -> bool:
    return index <= 2 or index > total - 2


def _infer_overlap_ms(prev_speaker: str | None, speaker: str, prev_text: str, text: str,
                      index: int, total: int, env: dict[str, str] | None = None) -> int:
    """Conservative auto-overlap for interruptions when no explicit hint exists."""
    if env is None:
        env = read_env()
    if env.get("PODCAST_AUTO_OVERLAP", "1").strip().lower() in {"0", "false", "no"}:
        return 0
    if not prev_speaker or prev_speaker == speaker or _is_fixed_opening_or_closing(index, total):
        return 0

    clean = _remove_nonspoken_hints(text)
    prev_clean = _remove_nonspoken_hints(prev_text)
    starts = (
        "等一下", "等等", "等会", "不是", "不是不是", "但", "但是", "可", "可是",
        "对对对", "是是是", "嗯嗯", "你这样", "我插一句", "拉回来", "啊？", "诶",
    )
    if clean.startswith(starts):
        return 360
    if prev_clean.endswith(("……", "…", "——", "就是", "不是", "应该说", "我觉得")):
        return 460
    if "(chuckle)" in clean or "(laughs)" in clean:
        return 180
    return 0


def _infer_tts_emotion(speaker: str, text: str, env: dict[str, str] | None = None,
                       default: str | None = None) -> tuple[str, str]:
    """
    Infer MiniMax voice_setting.emotion from the director/performance layer.

    The director decides emotion indirectly through wording + speech tags. This
    function maps that performance script to a segment-level emotion. The text
    returned is cleaned for TTS if an explicit [[emotion=...]] hint exists.
    """
    if env is None:
        env = read_env()
    allowed = _allowed_tts_emotions(env)
    default_emotion = (default or env.get("MINIMAX_TTS_DEFAULT_EMOTION") or "fluent").lower()
    if default_emotion not in allowed:
        default_emotion = "fluent" if "fluent" in allowed else ""

    explicit, cleaned = _extract_explicit_emotion(text)
    if explicit and explicit in allowed:
        return explicit, cleaned

    lower = cleaned.lower()
    tags = {m.group(1).lower() for m in re.finditer(r"\(([^)]+)\)", lower)}

    if tags & {"laughs", "chuckle", "snorts"}:
        candidate = "happy"
    elif tags & {"gasps"}:
        candidate = "surprised"
    elif tags & {"sighs", "groans"}:
        candidate = "sad"
    else:
        happy_words = ("好笑", "笑", "离谱", "荒诞", "有梗", "吐槽", "损", "可爱", "好玩", "都市传说")
        surprise_words = ("啊？", "突然", "没想到", "居然", "诶", "震惊", "惊讶")
        sad_words = ("担心", "可怕", "危险", "焦虑", "麻烦", "沉重", "严肃", "警惕")
        if any(w in cleaned for w in happy_words):
            candidate = "happy"
        elif any(w in cleaned for w in surprise_words):
            candidate = "surprised"
        elif any(w in cleaned for w in sad_words):
            candidate = "sad"
        else:
            candidate = default_emotion

    if candidate not in allowed:
        candidate = default_emotion
    return candidate, cleaned


def parse_script(text: str) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#") or line.startswith("```") or line.startswith("【"):
            continue
        if line.startswith("用户") or line.startswith("检查") or line.startswith("对于") or line.startswith("通过"):
            continue
        m = re.match(r"^(林深|若水)：(.+)$", line)
        if m:
            items.append((m.group(1), m.group(2).strip()))
    return items
