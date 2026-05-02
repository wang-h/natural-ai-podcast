#!/usr/bin/env python3
"""
podcast_engine — core functions for natural podcast generation.

Two main capabilities:
  1. generate_script() — any text → optimized podcast script (4-stage LLM pipeline)
  2. render_audio()   — podcast script → natural MP3 (MiniMax TTS + Deepling branding)

All state lives under output_dir; intermediate files are preserved for inspection.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_ENV = PROJECT_DIR / ".env"
SAMPLES_DIR = Path(os.environ.get("PODCAST_SAMPLES_DIR", str(PROJECT_DIR.parent / "podcast-edge-samples")))

INTRO_FILE = PROJECT_DIR / "assets" / "intro.mp3"
OUTRO_FILE = PROJECT_DIR / "assets" / "outro.mp3"

VOICE_BY_SPEAKER: dict[str, str] = {
    "林深": "Chinese (Mandarin)_Southern_Young_Man",
    "若水": "Chinese (Mandarin)_HK_Flight_Attendant",
}

SPEECH_TAG_NAMES = [
    "laughs", "chuckle", "coughs", "clear-throat", "groans",
    "breath", "pant", "inhale", "exhale", "gasps", "sniffs",
    "sighs", "snorts", "burps", "lip-smacking", "humming",
    "hissing", "emm", "sneezes",
]
SPEECH_TAG_RE = re.compile(r"\((?:{})\)".format("|".join(SPEECH_TAG_NAMES)), re.I)
PAUSE_RE = re.compile(r"<#\d+(?:\.\d+)?#>")

STAGE1_SYSTEM = """你是播客脚本编剧。请把下面素材改写成双人对谈播客脚本。

格式规则（绝对严格遵守）：
- 纯文本，无任何 Markdown。
- 每行一句话，格式：林深：... 或 若水：...
- 用中文全角冒号：连接说话人和内容。
- 行与行之间不留空行，连续书写。
- 不加标题、不加粗、不写舞台指示、不写"（笑）"等中文括号表演说明。
- 不加任何停顿标签或 MiniMax 情绪标签。

前两行固定（一字不改）：
林深：大家好，我是林深。
若水：我是若水，欢迎收听 DeepLing AI 播客。

最后两行固定（一字不改）：
林深：我是林深。
若水：我是若水，我们下期见。

内容规则：
- 保留原文事实，不编造新事实。
- 不添加原文没有的比喻、类比或例子。
- 不加入口头禅、语气词或停顿标记。
- 用原文的观点和信息，写成自然对话。"""

STAGE2_SYSTEM = """只调整下面脚本的对话节奏。不改变事实，不改变格式，不添加新比喻或类比。

格式规则：保持输入格式——纯文本、林深：/若水：开头、行间无空行、无 Markdown。

节奏目标：
- 70% 回合中等长度（15-60 字）。
- 20% 回合较短（4-15 字），作为接话点缀。
- 10% 回合可以较长（最长 80 字）。
- 不连续超过 3 个极短回合。
- 不把观点拆成清单式一人一句。
- 超过 80 字的长发言，拆开让另一位主持人确认、质疑或补充。
- 不加新事实、新比喻、新例子。"""

STAGE3_SYSTEM = """在下面脚本中加入少量聊天质感。不改变事实、结构和格式。不添加新比喻或类比。

格式规则：保持输入格式——纯文本、林深：/若水：开头、行间无空行、无 Markdown。

允许加入：
- 口语词：嗯、呃、怎么说呢
- 互动：对吧？你觉得呢？你说是不是？这样说会不会太绕？
- 回退修正：不是……应该说……、我换个说法
- 停顿标签（仅限半角尖括号）：<#0.2#>、<#0.25#>、<#0.3#>
- 情绪标签（仅限半角圆括号英文）：(chuckle)、(breath)、(emm)、(sighs)

禁止事项：
- 禁止 (laughs)、(pause) 或任何不在允许列表内的英文标签
- 禁止用全角中文括号写（笑）、（叹气）、（停顿）、（深呼吸）等
- 禁止停顿标签超过 <#0.3#>
- 禁止每句都加标签或口头禅
- 禁止在开头两行和结尾两行加任何标签或追加任何文字
- 禁止添加原文没有的比喻、类比、例子
- 禁止把对话退化成清单短句"""

STAGE4_SYSTEM = """审查并修正下面脚本。只输出修正后的脚本。

第一步：格式修正
- 移除一切 Markdown 格式
- 确保每行是 林深：... 或 若水：... 格式
- 消除行间空行
- 确保前两行严格是（不加标签不加字）：
  林深：大家好，我是林深。
  若水：我是若水，欢迎收听 DeepLing AI 播客。
- 确保最后两行严格是（不加标签不加字）：
  林深：我是林深。
  若水：我是若水，我们下期见。

第二步：标签修正
- 全角中文（笑）→ (chuckle)、（叹气/深呼吸）→ (breath) 或 (sighs)、（停顿）→ <#0.2#>
- 删除所有 (laughs)、(pause) 及不在允许列表中的英文标签
- 确保停顿标签只有 <#0.2#>、<#0.25#>、<#0.3#>
- 不要在开头问候和结尾告别行上加任何标签

第三步：内容修正
- 连续 4 个以上极短句 → 合并
- 超过 80 字以上的单人发言 → 拆开插入互动
- 每句都有标签 → 删掉多余标签
- 像文章朗读 → 加入少量犹豫、回退
- 出现原文没有的比喻或类比 → 删除"""

STAGE_FILES = ["01-base.md", "02-rhythm.md", "03-texture.md", "04-final.md"]
STAGE_SYSTEMS = [STAGE1_SYSTEM, STAGE2_SYSTEM, STAGE3_SYSTEM, STAGE4_SYSTEM]


# ---------------------------------------------------------------------------
# utilities
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


def run_ffmpeg(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def parse_script(text: str) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#") or line.startswith("```") or line.startswith("【"):
            continue
        m = re.match(r"^(林深|若水)：(.+)$", line)
        if m:
            items.append((m.group(1), m.group(2).strip()))
    return items


def _is_minimax_host(base_url: str) -> bool:
    try:
        href = base_url.strip()
        if not href.startswith("http"):
            href = f"https://{href}"
        return "minimax" in href
    except Exception:
        return False


# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------

def call_llm_openai(api_key: str, base_url: str, model: str, system: str, user: str) -> str:
    base = base_url.rstrip("/")
    url = f"{base}/chat/completions" if "/v1" in base else f"{base}/v1/chat/completions"
    body = {
        "model": model,
        "temperature": 0.55,
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
    return content


def call_llm_anthropic(api_key: str, base_url: str, model: str, system: str, user: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/v1/messages"):
        url = base
    elif base.endswith("/v1"):
        url = f"{base}/messages"
    elif base.endswith("/anthropic"):
        url = f"{base}/v1/messages"
    else:
        url = f"{base}/anthropic/v1/messages"

    body = {
        "model": model,
        "max_tokens": 16384,
        "temperature": 0.55,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if _is_minimax_host(base_url):
        headers.update({"Authorization": f"Bearer {api_key}", "x-api-key": api_key, "anthropic-version": "2023-06-01"})
    elif "api.anthropic.com" in base_url:
        headers.update({"x-api-key": api_key, "anthropic-version": "2023-06-01"})
    else:
        headers.update({"Authorization": f"Bearer {api_key}", "x-api-key": api_key, "anthropic-version": "2023-06-01"})

    req = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM(anthropic) HTTP {exc.code}: {detail}") from exc
    blocks = data.get("content") or []
    text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
    if not text:
        raise RuntimeError("LLM(anthropic) returned no content")
    return text


def call_llm(system: str, user: str, model: str, transport: str, api_key: str, base_url: str) -> str:
    for attempt in range(4):
        try:
            if transport == "anthropic":
                return call_llm_anthropic(api_key, base_url, model, system, user)
            else:
                return call_llm_openai(api_key, base_url, model, system, user)
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


# ---------------------------------------------------------------------------
# MiniMax TTS
# ---------------------------------------------------------------------------

def minimax_tts(api_key: str, base_url: str, model: str, text: str, voice_id: str) -> bytes:
    supports_tags = model in ("speech-2.8-hd", "speech-2.8-turbo")
    clean_text = text
    if not supports_tags:
        clean_text = SPEECH_TAG_RE.sub("", text)
        clean_text = PAUSE_RE.sub("", clean_text)

    url = base_url.rstrip("/") + "/v1/t2a_v2"
    body = {
        "model": model, "text": clean_text, "stream": False,
        "language_boost": "Chinese", "output_format": "hex",
        "voice_setting": {"voice_id": voice_id, "speed": 1, "vol": 1, "pitch": 0, "emotion": "fluent"},
        "audio_setting": {"sample_rate": 32000, "bitrate": 128000, "format": "mp3", "channel": 1},
        "aigc_watermark": False,
    }
    req = urllib.request.Request(
        url, data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST",
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace").lower()
            if any(k in detail for k in ("rate limit", "rpm", "429")):
                time.sleep(15 * (attempt + 1))
                continue
            raise RuntimeError(f"MiniMax TTS HTTP {exc.code}") from exc

        status = payload.get("base_resp", {}).get("status_code")
        if status not in (None, 0):
            raise RuntimeError(f"MiniMax TTS failed: {payload.get('base_resp', {}).get('status_msg') or status}")
        audio = payload.get("data", {}).get("audio") or payload.get("audio_file")
        if not audio:
            raise RuntimeError("MiniMax returned no audio")
        return bytes.fromhex(audio.strip())

    raise RuntimeError("MiniMax TTS failed after 4 retries")


# ---------------------------------------------------------------------------
# audio assembly
# ---------------------------------------------------------------------------

def _concat_reencode(infiles: list[Path], output: Path) -> None:
    inputs: list[str] = []
    for f in infiles:
        inputs.extend(["-i", str(f)])
    n = len(infiles)
    labels = "".join(f"[a{i}]" for i in range(n))
    run_ffmpeg(["ffmpeg", "-y", "-hide_banner", *inputs,
                "-filter_complex", f"{labels}concat=n={n}:v=0:a=1,loudnorm=I=-16:TP=-1.5:LRA=11[a]",
                "-map", "[a]", "-codec:a", "libmp3lame", "-b:a", "160k", str(output)])


def _concat_deepling(intro: Path, dialogue: Path, outro: Path, output: Path) -> None:
    run_ffmpeg(["ffmpeg", "-y", "-hide_banner",
                "-i", str(intro), "-i", str(dialogue), "-i", str(outro),
                "-filter_complex",
                "[0:a]aresample=44100,aformat=channel_layouts=stereo[a0];"
                "[1:a]aresample=44100,aformat=channel_layouts=stereo[a1];"
                "[2:a]aresample=44100,aformat=channel_layouts=stereo[a2];"
                "[a0][a1][a2]concat=n=3:v=0:a=1,loudnorm=I=-16:TP=-1.5:LRA=11[a]",
                "-map", "[a]", "-codec:a", "libmp3lame", "-b:a", "160k", str(output)])


def _soften(input_path: Path, output_path: Path) -> None:
    script = SAMPLES_DIR / "podcast_soft_edges_test.py"
    run_ffmpeg([sys.executable, str(script), str(input_path), str(output_path),
                "--head-ms", "380", "--tail-ms", "320", "--head-volume", "0.75",
                "--tail-volume", "0.60", "--fade-ms", "80", "--lowpass", "12000"])


def _download_intro_outro(run_dir: Path) -> tuple[Path, Path]:
    intro = run_dir / "minimax-intro.mp3"
    outro = run_dir / "minimax-outro.mp3"
    if not intro.exists():
        urllib.request.urlretrieve(INTRO_URL, intro)
    if not outro.exists():
        urllib.request.urlretrieve(OUTRO_URL, outro)
    return intro, outro


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------

def resolve_llm_config(env: dict[str, str] | None = None, *,
                       transport: str = "anthropic",
                       api_key: str | None = None,
                       base_url: str | None = None,
                       model: str | None = None) -> dict[str, str]:
    """Resolve LLM config from env + overrides. Returns {api_key, base_url, model, transport}."""
    if env is None:
        env = read_env()
    key = api_key or env.get("OPENAI_API_KEY") or env.get("ANTHROPIC_API_KEY") or env.get("MINIMAX_API_KEY") or ""
    if transport == "anthropic":
        base = base_url or env.get("ANTHROPIC_BASE_URL") or "https://api.minimaxi.com/anthropic"
        m = model or env.get("ANTHROPIC_MODEL") or "MiniMax-Text-01"
    else:
        base = base_url or env.get("OPENAI_BASE_URL") or "https://api.minimaxi.com/v1"
        m = model or env.get("OPENAI_MODEL") or "MiniMax-Text-01"
    return {"api_key": key, "base_url": base, "model": m, "transport": transport}


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


# --- Feature 1: Text → Script ---

def generate_script(source_text: str, output_dir: Path, *,
                    llm_config: dict[str, str] | None = None,
                    log_fn=None) -> dict:
    """
    Run 4-stage LLM pipeline: source text → optimized podcast script.

    Returns dict with keys: final_script, stages[list of {name, path, chars}], output_dir.
    Intermediate files are written to output_dir (01-base.md ... 04-final.md).
    """
    if llm_config is None:
        llm_config = resolve_llm_config()

    output_dir.mkdir(parents=True, exist_ok=True)
    current = source_text
    stages_result: list[dict] = []

    for i, (filename, system) in enumerate(zip(STAGE_FILES, STAGE_SYSTEMS)):
        out_path = output_dir / filename

        if out_path.exists():
            current = out_path.read_text(encoding="utf-8")
            stages_result.append({"name": filename, "path": str(out_path), "chars": len(current), "reused": True})
            continue

        prefix = "素材：\n" if i == 0 else "脚本：\n"
        if log_fn:
            log_fn(f"  Stage {i+1}/4: {filename} ...")
        result = call_llm(system, prefix + current,
                          llm_config["model"], llm_config["transport"],
                          llm_config["api_key"], llm_config["base_url"])
        out_path.write_text(result, encoding="utf-8")
        current = result
        stages_result.append({"name": filename, "path": str(out_path), "chars": len(result), "reused": False})
        if log_fn:
            log_fn(f"  -> {filename} ({len(result)} chars)")

    return {
        "final_script": current,
        "stages": stages_result,
        "output_dir": str(output_dir),
    }


# --- Feature 2: Script → Audio ---

def render_audio(script_text: str, output_dir: Path, *,
                 tts_config: dict[str, str] | None = None,
                 env: dict[str, str] | None = None,
                 soft_edges: bool = True,
                 deepling_branding: bool = True,
                 force_tts: bool = False,
                 log_fn=None) -> dict:
    """
    Render a podcast script to MP3 audio.

    Returns dict with keys: raw_path, soft_path, deepling_path, segments[list of Path].
    """
    if tts_config is None:
        tts_config = resolve_tts_config()
    if env is None:
        env = read_env()

    items = parse_script(script_text)
    if not items:
        raise ValueError("No dialogue lines found in script")

    seg_dir = output_dir / "segments"
    seg_dir.mkdir(parents=True, exist_ok=True)

    seg_soft_dir = output_dir / "segments-soft" if soft_edges else None
    if seg_soft_dir:
        seg_soft_dir.mkdir(parents=True, exist_ok=True)

    raw_files: list[Path] = []
    soft_files: list[Path] = []

    for idx, (speaker, text) in enumerate(items, 1):
        voice_id = VOICE_BY_SPEAKER.get(speaker, env.get("MINIMAX_TTS_VOICE_ID", "Chinese (Mandarin)_Warm_Bestie"))
        raw_path = seg_dir / f"{idx:02d}-{speaker}.mp3"

        if log_fn:
            snippet = text[:60] + ("..." if len(text) > 60 else "")
            log_fn(f"  {idx:02d}/{len(items):02d} {speaker}: {snippet}")

        if force_tts or not raw_path.exists() or raw_path.stat().st_size == 0:
            raw_path.write_bytes(minimax_tts(
                tts_config["api_key"], tts_config["base_url"], tts_config["model"], text, voice_id))
            time.sleep(0.8)
        raw_files.append(raw_path)

        if seg_soft_dir:
            soft_path = seg_soft_dir / f"{idx:02d}-{speaker}.mp3"
            if force_tts or not soft_path.exists() or soft_path.stat().st_size == 0:
                _soften(raw_path, soft_path)
            soft_files.append(soft_path)

    # assemble
    raw_final = output_dir / "final_raw.mp3"
    _concat_reencode(raw_files, raw_final)

    soft_final = output_dir / "final_soft.mp3" if soft_files else None
    if soft_files:
        _concat_reencode(soft_files, soft_final)

    deepling_final = output_dir / "final_deepling.mp3" if deepling_branding else None
    if deepling_branding:
        intro_p, outro_p = _download_intro_outro(output_dir)
        dialogue_p = output_dir / "final_dialogue.mp3"
        _concat_reencode(raw_files, dialogue_p)
        _concat_deepling(intro_p, dialogue_p, outro_p, deepling_final)

    return {
        "raw_path": str(raw_final),
        "soft_path": str(soft_final) if soft_final else None,
        "deepling_path": str(deepling_final) if deepling_final else None,
        "segments": [str(p) for p in raw_files],
        "line_count": len(items),
    }
