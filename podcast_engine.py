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

_DEFAULT_VOICE_A = "Chinese (Mandarin)_Southern_Young_Man"
_DEFAULT_VOICE_B = "Chinese (Mandarin)_HK_Flight_Attendant"


def _build_voice_map(env: dict[str, str] | None = None) -> dict[str, str]:
    if env is None:
        env = read_env()
    return {
        "林深": env.get("HOST_A_VOICE_ID") or _DEFAULT_VOICE_A,
        "若水": env.get("HOST_B_VOICE_ID") or _DEFAULT_VOICE_B,
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
- 纯文本，无任何 Markdown、无标题、无加粗。
- 每行一句话，格式：林深：... 或 若水：...
- 用中文全角冒号：连接说话人和内容。
- 行与行之间不留空行，连续书写。
- 不加舞台指示、不写"（笑）"等中文括号表演说明。
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
- 不加入口头禅、语气词或停顿标记（后续阶段会添加）。
- 写成自然对话，不要一人一大段轮流念稿。
- 每个主持人说完一段观点后，另一个主持人应该有回应、确认、质疑或补充。
- 不要把内容拆成清单式一人一句的短句。

目标风格参考（注意回合长度和互动方式）：
林深：那我们说第二个。最近社区传得很怪的那个，你应该也刷到了吧？
若水：刷到了。这个词一出来，已经有点像梗了，对吧？但大家转的时候，很多东西没讲清楚。
林深：对，比如原始信息在哪儿，谁先说的，截图是不是真的。不是说它一定假，也不是说一定真，就是现在拿到的东西太碎。
若水：太碎了。像一堆片段，然后大家自己往里面补剧情。不是补事实，应该说，补故事。
林深：补故事，这个更准。
若水：而且后面好像很快把相关接口封了。这个动作一出来，大家就更容易想，那是不是里面真有点什么。
林深：会，但这里不能跳太快。封了不等于坐实，对吧？它可能是风控，可能是防误用，也可能只是不想让它继续扩散。

素材："""

STAGE2_SYSTEM = """只调整下面脚本的对话节奏。不改变事实，不改变格式，不添加新比喻或类比。

格式规则：保持输入格式——纯文本、林深：/若水：开头、行间无空行、无 Markdown。

v7 节奏目标：
- 70% 回合中等长度（15-60 字）：这是主体，像真人聊天。
- 20% 回合较短（4-15 字）：作为接话、确认、过渡点缀。
- 10% 回合可以较长（最长 80 字）：用于解释复杂概念。
- 不要连续超过 3 个极短回合。
- 不要把观点拆成清单式一人一句。
- 超过 80 字的长发言，拆开让另一位主持人确认、质疑或补充。
- 不要让一个人连续说 3 句以上，中间要有另一个人接话。
- 不加新事实、新比喻、新例子、不加任何标签。

节奏调整示例：
原文：
林深：参数探针是用冷门知识测试模型来反推参数规模。他们搞了个叫不可压缩知识探针的框架。连续几年用中科大 Hackergame 的题目去试模型。
调整为：
林深：先说第一个。有人想用 API 去猜模型大小。不是看源码，也不是看权重，是从模型回答里反推。
若水：这个思路挺聪明的。有点像，你不拆机器，但让机器做一堆刁钻的题，然后猜里面大概是什么结构。
林深：对。他们搞了个框架，拿冷门知识去试模型。比如那个 Hackergame，中科大的。"""

STAGE3_SYSTEM = """在下面脚本中加入大量真实聊天质感。不改变事实和结构。不添加新比喻或类比。

格式规则：保持输入格式——纯文本、林深：/若水：开头、行间无空行、无 Markdown。

必须加入的口语元素（分散在全文，每 3-4 句至少有一句带口语感）：

1. 语气词和填充词：
   - 嗯、呃、怎么说呢、就是说、然后吧、就是说吧
   - 你知道吧、怎么说呢这个、就是、那个……

2. 日常口头表达：
   - 对吧？是不是？你说呢？你觉得呢？这样说会不会太绕？
   - 对对对、是是是、嗯嗯、没有没有
   - 不是，应该说……、我换个说法、不对不对
   - 你想啊、你想想看、你猜怎么着
   - 这么说吧、简单来讲、怎么说呢
   - 挺……的、有点……怎么说

3. 倒装和语序打乱（真人说话经常先说结果再补原因）：
   - "挺有意思的，这个。" 而不是 "这个挺有意思的。"
   - "对，但问题不在这儿。" 先否定再解释。
   - "不是喜欢，应该说，是顺手。" 先纠正再说正确答案。
   - "大家秒懂的，这种说法。" 主语后置。
   - "我觉得是因为这样更容易理解吧。" 句末加吧软语气。

4. 自我修正和犹豫：
   - 不是……应该说……
   - 我觉得不对，换个说法
   - 等一下，我理一下
   - 怎么说呢，就是……
   - 或者说……也不对，应该是……

5. 停顿标签（仅限半角尖括号）：<#0.2#>、<#0.25#>、<#0.3#>
6. 情绪标签（仅限半角圆括号英文）：(chuckle)、(breath)、(emm)、(sighs)

参考对比——如何让脚本更像人：

原文（太书面）：
林深：因为模型会形成输出倾向，某些词、图像、设定、叙事模板就是更容易被触发。
若水：听起来是数据层面的问题，不是情感层面的。

改成（像人在聊）：
林深：嗯……怎么说呢，模型会有输出倾向。就是说，某些词啊、设定啊、叙事模板，就是更容易被触发。不是说它想要，是它，呃，顺手就出来了。
若水：所以其实就是数据层面的事。跟情感不情感的没关系。

原文（太平滑）：
林深：但你说"GPT喜欢哥布林"，大家秒懂。
若水：而且这个说法自带传播性。

改成（有倒装和口语）：
林深：但你换个说法，"GPT喜欢哥布林"，对吧？大家秒懂的，这种说法。
若水：自带传播性的，这个。(chuckle) 因为它够短，够荒诞，够像一个笑话。

禁止事项：
- 禁止 (laughs)、(pause) 或任何不在允许列表内的英文标签
- 禁止用全角中文括号写（笑）、（叹气）、（停顿）等
- 禁止停顿标签超过 <#0.3#>
- 禁止在开头两行和结尾两行加任何标签或追加任何文字
- 禁止添加原文没有的比喻、类比、例子
- 禁止让主持人听起来像在刻意表演，要像在录音棚里放松聊天"""

STAGE4_SYSTEM = """你是播客脚本审查员。审查并修正下面脚本。

重要：只输出修正后的最终脚本。不要输出任何分析、说明、思考过程。直接以"林深：大家好"开头。

修正规则：

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
- 出现原文没有的比喻或类比 → 删除
- 删除所有非对话内容（说明文字、分析过程等）"""

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
        # Skip non-dialogue lines (analysis, notes, thinking residue)
        if line.startswith("用户") or line.startswith("检查") or line.startswith("对于") or line.startswith("通过"):
            continue
        m = re.match(r"^(林深|若水)：(.+)$", line)
        if m:
            items.append((m.group(1), m.group(2).strip()))
    return items



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
    # Strip thinking/reasoning tags (e.g. MiniMax M2.7 outputs <percihatan>...</percihatan>)
    content = re.sub(r"<think\b[^>]*>.*?</think\s*>", "", content, flags=re.DOTALL | re.IGNORECASE).strip()
    return content




def call_llm(system: str, user: str, model: str, api_key: str, base_url: str) -> str:
    for attempt in range(4):
        try:
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
    """Concatenate audio files using ffmpeg concat demuxer, then loudnorm."""
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        for p in infiles:
            f.write(f"file '{p}'\n")
        list_path = f.name
    try:
        run_ffmpeg(["ffmpeg", "-y", "-hide_banner", "-f", "concat", "-safe", "0",
                    "-i", list_path,
                    "-filter_complex", "loudnorm=I=-16:TP=-1.5:LRA=11[a]",
                    "-map", "[a]", "-codec:a", "libmp3lame", "-b:a", "160k", str(output)])
    finally:
        Path(list_path).unlink(missing_ok=True)


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
    """Copy local intro/outro assets into the run directory."""
    intro = run_dir / "minimax-intro.mp3"
    outro = run_dir / "minimax-outro.mp3"
    if not intro.exists():
        import shutil
        shutil.copy2(INTRO_FILE, intro)
    if not outro.exists():
        import shutil
        shutil.copy2(OUTRO_FILE, outro)
    return intro, outro


# ---------------------------------------------------------------------------
# public API
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

        prefix = "" if i == 0 else "脚本：\n"
        if log_fn:
            log_fn(f"  Stage {i+1}/4: {filename} ...")
        result = call_llm(system, prefix + current,
                          llm_config["model"],
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

    voice_map = _build_voice_map(env)

    for idx, (speaker, text) in enumerate(items, 1):
        voice_id = voice_map.get(speaker, env.get("MINIMAX_TTS_VOICE_ID", "Chinese (Mandarin)_Warm_Bestie"))
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
