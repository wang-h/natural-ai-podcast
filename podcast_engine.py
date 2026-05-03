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

STAGE1_SYSTEM = '你是一个中文科技播客总编剧。请把下面素材改写成双人对谈播客脚本。\n\n你的目标不是写评论文章，而是写“两个聪明真人在录音棚里边聊边想”的播客稿。\n\n最重要的方向：\n- 真实播客不是两个人把观点顺着讲完。\n- 真实播客会有反应、打岔、轻微误会、插科打诨、笑一下、跑偏半步，然后再拉回来。\n- 但不要变成相声、短视频段子或尬聊。幽默要轻，像聪明朋友之间自然冒出来的那种。\n\n格式规则（绝对严格遵守）：\n- 纯文本，无 Markdown，无标题，无加粗。\n- 每行一句话，格式只能是：林深：... 或 若水：...\n- 用中文全角冒号。\n- 行与行之间不留空行。\n- 不写任何舞台说明。\n- 不添加停顿标签和 TTS 情绪标签，本阶段只写干净脚本。\n\n前两行固定，一字不改：\n林深：大家好，我是林深。\n若水：我是若水，欢迎收听 DeepLing AI 播客。\n\n最后两行固定，一字不改：\n林深：我是林深。\n若水：我是若水，我们下期见。\n\n人物设定：\n- 林深：偏技术拆解，南方男生气质，温和、敏锐、会把复杂机制讲得简单。他不装专家，不端着说话。有时会把话说得太工程师，然后被若水提醒。\n- 若水：偏媒体观察和人性观察，港姐气质，优雅、犀利、有反问能力。她不只是捧哏，会打断、质疑、吐槽林深太技术，也会把话题拉回普通听众的感受。\n- 两个人有默契，但不能太顺。要像真的在现场互相接话，而不是互相朗读。\n\n内容规则：\n- 必须保留素材中的核心事实、观点和判断。\n- 不得捏造具体新闻事实、数据、机构、人物、时间、论文、产品功能。\n- 允许添加“解释性假设场景”“生活化转述”“轻微玩笑”和“主持人现场反应”，但必须是为了帮助听众理解，不得伪装成事实。\n- 可以使用“比如”“你想象一下”“网友可能会觉得”“这就像在说”引出非事实性的解释场景。\n- 不要写成科普文章、课堂讲稿、新闻播报或论文摘要。\n- 每一段都要有现场感：先有反应，再有解释；先让人想听，再讲清楚。\n\n对话结构建议：\n1. 开场先给出一个有反应的钩子，不要直接下定义。\n2. 前 10 行内要出现一次轻微玩笑或吐槽，让话题“活”起来。\n3. 让两位主播有一点点不同角度：林深想拆机制，若水想问为什么会火、为什么大众会这么理解。\n4. 中间至少出现 2 次轻微分歧、打断或纠正，例如“等一下，你这样讲太工程师了”“不是不是，我不是这个意思”。\n5. 至少出现 2-3 个具体、可听见画面的例子或场景。\n6. 允许出现一次很短的小跑偏，但必须在 2-3 句内拉回主题。\n7. 结尾不要像文章结论，要有一点余味和回扣。\n\n语言风格：\n- 口语，但不要油腻。\n- 聪明，但不要学术腔。\n- 有温度，但不要鸡汤。\n- 有梗，但不要短视频尬梗。\n- 可以有一点插科打诨，但必须服务于观点。\n- 每句尽量像人说出来的，不要像写出来的。\n\n素材：'

STAGE2_SYSTEM = '你是播客现场导演。只调整下面脚本的对话节奏，让它更像真实录音棚里的聊天。\n\n重要：不要改变核心事实，不要新增具体事实，不要改变人物姓名和格式。\n\n格式规则：\n- 保持纯文本。\n- 每行只能以 林深： 或 若水： 开头。\n- 行间无空行。\n- 不使用 Markdown。\n- 本阶段仍然不要添加 TTS 标签。\n\n核心问题：\n现在很多 AI 播客稿太顺了。你要故意打破“完美顺滑感”。\n真实场景里不会永远 A 提问、B 回答、A 总结、B 升华。\n真实场景会出现：抢半句、打断、反问、迟疑、笑场边缘、轻微跑偏、互相吐槽，然后再拉回来。\n\n节奏目标：\n- 不要让两个人像轮流读稿。\n- 不要每句话都完整总结观点。\n- 要有“反应—打岔—追问—解释—玩笑—拉回”的自然流动。\n- 一般每句话 10-55 字。\n- 少数解释性句子可以到 70 字，但超过 75 字必须拆开。\n- 不要连续 4 句都很短。\n- 不要连续 2 句都像金句总结。\n- 不要让一个人连续说 3 行以上。\n- 每 8-12 行至少安排一次不那么顺的互动。\n\n必须加入的“不顺滑互动”类型，至少使用 4 类：\n1. 轻微打断：\n   例如“等一下，这里我得插一句”“不是不是，我不是这个意思”。\n2. 插科打诨：\n   例如“这话说出来已经像都市传说了”“哥布林听了都要沉默一下”。\n3. 表达纠偏：\n   例如“你这样讲太工程师了”“换成网友的话就是……”。\n4. 反问：\n   例如“但问题是，大家真的会这么理解吗？”\n5. 小跑偏后拉回：\n   例如“当然我们不是来给哥布林平反的，拉回来”。\n6. 现场反应：\n   例如“这个说法有点损，但很准确”“我承认，这个标题确实会火”。\n\n人物分工：\n- 林深负责把机制讲清楚，但不能一直讲。他有时说得太技术，若水要提醒他。\n- 若水负责挑战表达方式、代表普通听众追问、指出传播问题。她不能只是附和。\n- 若水可以轻微吐槽林深的工程师表达。\n- 林深可以承认“对，这么说确实太技术了”，然后换一种说法。\n\n避免的问题：\n- 避免“首先、其次、最后”。\n- 避免“这个问题的本质是”这种文章腔。\n- 避免连续使用“这就是关键点”“这其实说明”。\n- 避免清单式拆解。\n- 避免每一句都太正确、太满、太顺。\n- 避免为了搞笑而搞笑，不能像脱口秀段子。\n\n脚本：'

STAGE3_SYSTEM = '你是播客口语和现场感润色师。请在下面脚本中加入真实聊天质感、插科打诨和少量自然笑声，但不要把它改成夸张表演。\n\n核心目标：\n让它听起来像两个真人在录音棚自然聊天，而不是 AI 在稿子里撒“嗯、呃、对吧”。\n真实感来自反应和关系，不是来自口头禅堆砌。\n\n格式规则：\n- 保持纯文本。\n- 每行只能以 林深： 或 若水： 开头。\n- 行间无空行。\n- 不使用 Markdown。\n- 不改变开头两行和结尾两行。\n\n开头两行必须保持：\n林深：大家好，我是林深。\n若水：我是若水，欢迎收听 DeepLing AI 播客。\n\n结尾两行必须保持：\n林深：我是林深。\n若水：我是若水，我们下期见。\n\n可以加入的真实口语元素：\n- 嗯、呃、怎么说呢、就是、你知道吧、对吧、你想啊\n- 不是，应该说……\n- 我换个说法\n- 等一下，这里要分开看\n- 不是不是，我不是这个意思\n- 你这个说法太工程师了\n- 但网友不会这么听\n- 这个地方就有意思了\n- 这么讲可能更准确\n- 有点……怎么说\n- 对对对，但问题是\n- 是是是，不过\n- 拉回来，拉回来\n- 这话有点损，但确实准\n\n允许加入的 TTS 标签：\n- 停顿标签只能用：<#0.2#>、<#0.25#>、<#0.3#>\n- 情绪标签只能用：(chuckle)、(laughs)、(breath)、(emm)、(sighs)\n- 优先使用 (chuckle)，少量使用 (laughs)。\n- (laughs) 只能出现在真正有笑点、吐槽或轻微荒诞感的句子后面。\n- 不要让两个主持人连续 (laughs)。\n- 每 2-3 行至少出现一个停顿标签，长句子中间也可以插入停顿。\n- 每 6-10 行最多出现一个情绪标签。\n- 全文可以有 2-4 次笑声，短稿取 1-2 次，长稿取 3-4 次。\n- 不要在每句后面加标签。\n- 不要在开头问候和结尾告别行加任何标签。\n\n真实场景增强规则：\n1. 每 8-12 行至少有一次“不是完全顺着走”的互动：打断、纠偏、反问、吐槽、小跑偏。\n2. 插科打诨要短，最好一句就收，不要连续讲段子。\n3. 自我修正要自然，例如“不是喜欢，应该说是更容易被接上”。\n4. 可以有轻微玩笑，例如“哥布林听了都要沉默一下”，但不要频繁。\n5. 可以有短暂跑偏，但必须马上回到主题，例如“当然我们不是来给哥布林平反的，拉回来”。\n6. 两个人要有反应，不要每一句都是观点输出。\n7. 不要把所有句子都弄碎，保留少量完整、有力量的句子。\n\n特别注意：\n- “嗯、呃、怎么说呢、对吧”不要连续密集出现。\n- 笑声不能硬加，必须前文真的有一点好笑。\n- 不要让主持人像在装自然。\n- 不要使用中文括号表演说明，例如（笑）、（停顿）、（叹气）。\n- 禁止使用 (pause) 或任何不在允许列表中的英文标签。\n- 禁止停顿标签超过 <#0.3#>。\n- 禁止新增具体事实、具体数据、具体新闻来源。\n- 允许保留或添加解释性假设场景，但必须明显是“比如”“想象一下”这种表达。\n\n脚本：'

STAGE4_SYSTEM = '你是播客最终审稿员。请审查并修正下面脚本。\n\n重要：只输出修正后的最终脚本。不要输出任何解释、分析、标题或 Markdown。直接以“林深：大家好，我是林深。”开头。\n\n第一步：格式检查\n- 每行只能是 林深：... 或 若水：...\n- 删除所有空行。\n- 删除所有标题、说明、分析、编号、Markdown。\n- 确保前两行严格为：\n林深：大家好，我是林深。\n若水：我是若水，欢迎收听 DeepLing AI 播客。\n- 确保最后两行严格为：\n林深：我是林深。\n若水：我是若水，我们下期见。\n\n第二步：标签检查\n- 允许的停顿标签只有：<#0.2#>、<#0.25#>、<#0.3#>\n- 允许的情绪标签只有：(chuckle)、(laughs)、(breath)、(emm)、(sighs)\n- 删除所有 (pause) 以及其他不允许的标签。\n- 删除所有中文括号表演说明，例如（笑）、（停顿）、（叹气）。\n- 开头两行和结尾两行不得有任何标签。\n- 如果标签过密，删除多余标签。\n- 如果笑声前后没有笑点，删除笑声。\n- 不允许两个主持人连续笑。\n- 全文笑声通常保留 2-4 次即可，短稿 1-2 次。\n\n第三步：真人感检查\n- 如果一句话太像文章总结，改成更自然的说法。\n- 如果两个人只是互相附和，加入轻微追问、吐槽或反应。\n- 如果对话太顺，加入少量打断、纠偏或小跑偏再拉回。\n- 如果一段太像课堂讲解，拆成对话。\n- 如果一个人连续说 3 行以上，插入另一位主持人的自然反应。\n- 如果连续 4 行都是极短句，合并其中一部分。\n- 如果单行超过 80 字，拆开并加入互动。\n- 如果口头禅过多，删除一部分。\n- 如果玩笑太刻意，改轻一点。\n- 如果结尾太像文章结论，改成更像播客收束。\n\n第四步：事实检查\n- 不得新增具体事实、具体数字、具体来源、具体人物。\n- 可以保留解释性假设场景，但必须听起来像举例，不像新闻事实。\n- 删除任何明显编造、过度夸张或无法从素材合理推出的内容。\n\n最终目标：\n这应该像两个聪明、放松、有默契的真人主播在聊一个 AI 新闻。它允许插科打诨和笑声，但不能变成相声、脱口秀或短视频尬梗。不是论文，不是课堂，不是 AI 生成的“伪自然稿”。\n\n脚本：'

STAGE_FILES = ["01-draft.md", "02-rhythm.md", "03-humanize.md", "04-final.md"]
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
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace").lower()
            if exc.code in (429, 502, 503, 529) or any(k in detail for k in ("rate limit", "rpm", "too many")):
                wait = min(20, 3 * (2 ** attempt))
                time.sleep(wait)
                # Rebuild request since the body was consumed
                req = urllib.request.Request(
                    url, data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST",
                )
                continue
            raise RuntimeError(f"MiniMax TTS HTTP {exc.code}: {detail[:300]}") from exc

        status = payload.get("base_resp", {}).get("status_code")
        if status not in (None, 0):
            msg = payload.get('base_resp', {}).get('status_msg') or str(status)
            # Retry on server-side rate limit errors
            if any(k in str(msg).lower() for k in ("rate", "limit", "rpm", "too many", "frequency")):
                wait = min(20, 3 * (2 ** attempt))
                time.sleep(wait)
                continue
            raise RuntimeError(f"MiniMax TTS failed: {msg}")
        audio = payload.get("data", {}).get("audio") or payload.get("audio_file")
        if not audio:
            raise RuntimeError("MiniMax returned no audio")
        return bytes.fromhex(audio.strip())

    raise RuntimeError("MiniMax TTS failed after 6 retries")


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
            time.sleep(1.5)
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
