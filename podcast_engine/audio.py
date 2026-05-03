"""Audio assembly: timeline mixing, ffmpeg helpers, branding."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .config import INTRO_FILE, OUTRO_FILE, SAMPLES_DIR, read_env


def run_ffmpeg(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _env_int(env: dict[str, str], key: str, default: int) -> int:
    try:
        return int(str(env.get(key, default)).strip())
    except Exception:
        return default


def _env_bool(env: dict[str, str], key: str, default: bool = True) -> bool:
    raw = str(env.get(key, "1" if default else "0")).strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _trim_audio_edges(seg, *, keep_silence_ms: int = 70, silence_thresh_db: int = -42):
    """Trim leading/trailing TTS dead air while preserving a little room tone."""
    try:
        from pydub.silence import detect_nonsilent
    except Exception:
        return seg
    if len(seg) <= 0:
        return seg
    threshold = min(silence_thresh_db, int(seg.dBFS - 16)) if seg.dBFS != float("-inf") else silence_thresh_db
    ranges = detect_nonsilent(seg, min_silence_len=80, silence_thresh=threshold, seek_step=10)
    if not ranges:
        return seg
    start = max(0, ranges[0][0] - keep_silence_ms)
    end = min(len(seg), ranges[-1][1] + keep_silence_ms)
    return seg[start:end]


def _duck_tail(seg, duck_ms: int, duck_db: float):
    if duck_ms <= 0 or len(seg) <= 0:
        return seg
    duck_ms = min(duck_ms, len(seg))
    head = seg[:-duck_ms]
    tail = seg[-duck_ms:].apply_gain(duck_db)
    tail = tail.fade_out(min(80, max(20, duck_ms // 4)))
    return head + tail


def _assemble_dialogue_timeline(infiles: list[Path], segment_meta: list[dict], output: Path,
                                env: dict[str, str], *, natural_timing: bool = True) -> None:
    """
    Assemble dialogue on a timeline instead of simple concatenation.

    Supports real podcast turn-taking with overlap/interrupt/gap timing.
    """
    if not natural_timing:
        _concat_reencode(infiles, output)
        return

    try:
        from pydub import AudioSegment
    except Exception:
        _concat_reencode(infiles, output)
        return

    if not infiles:
        raise ValueError("No audio segments to assemble")

    turn_gap_ms = _env_int(env, "PODCAST_TURN_GAP_MS", 90)
    trim_edges = _env_bool(env, "PODCAST_TRIM_SILENCE", True)
    keep_silence_ms = _env_int(env, "PODCAST_KEEP_SILENCE_MS", 70)
    silence_thresh_db = _env_int(env, "PODCAST_SILENCE_THRESH_DB", -42)
    duck_db = float(env.get("PODCAST_INTERRUPT_DUCK_DB", "-8"))
    duck_extra_ms = _env_int(env, "PODCAST_INTERRUPT_DUCK_EXTRA_MS", 180)
    max_overlap_ms = _env_int(env, "PODCAST_MAX_OVERLAP_MS", 700)

    loaded = []
    for p in infiles:
        seg = AudioSegment.from_file(p)
        seg = seg.set_frame_rate(44100).set_channels(2)
        if trim_edges:
            seg = _trim_audio_edges(seg, keep_silence_ms=keep_silence_ms, silence_thresh_db=silence_thresh_db)
        loaded.append(seg)

    processed = []
    for i, seg in enumerate(loaded):
        next_overlap = 0
        if i + 1 < len(segment_meta):
            next_overlap = int(segment_meta[i + 1].get("overlap_ms") or 0)
        if next_overlap > 0:
            seg = _duck_tail(seg, min(max_overlap_ms, next_overlap + duck_extra_ms), duck_db)
        processed.append(seg)

    positions: list[int] = []
    cursor = 0
    for i, seg in enumerate(processed):
        if i == 0:
            pos = 0
        else:
            meta = segment_meta[i]
            overlap_ms = min(max_overlap_ms, max(0, int(meta.get("overlap_ms") or 0)))
            gap_ms = int(meta.get("gap_ms") or 0)
            pos = cursor + turn_gap_ms + gap_ms - overlap_ms
            pos = max(0, pos)
        positions.append(pos)
        cursor = max(cursor, pos + len(seg))

    timeline = AudioSegment.silent(duration=cursor + 250, frame_rate=44100).set_channels(2)
    for seg, pos in zip(processed, positions):
        if pos > 0:
            seg = seg.fade_in(15)
        timeline = timeline.overlay(seg, position=pos)

    tmp = output.with_suffix(".timeline_tmp.wav")
    timeline.export(tmp, format="wav")
    try:
        run_ffmpeg(["ffmpeg", "-y", "-hide_banner", "-i", str(tmp),
                    "-filter_complex", "loudnorm=I=-16:TP=-1.5:LRA=11[a]",
                    "-map", "[a]", "-codec:a", "libmp3lame", "-b:a", "160k", str(output)])
    finally:
        tmp.unlink(missing_ok=True)


def _concat_reencode(infiles: list[Path], output: Path) -> None:
    """Concatenate audio files using ffmpeg concat demuxer, then loudnorm."""
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
        shutil.copy2(INTRO_FILE, intro)
    if not outro.exists():
        shutil.copy2(OUTRO_FILE, outro)
    return intro, outro
