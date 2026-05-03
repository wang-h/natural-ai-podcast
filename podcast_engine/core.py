"""Core public API: generate_script and render_audio."""

from __future__ import annotations

import json
import time
from pathlib import Path

from .audio import (
    _assemble_dialogue_timeline,
    _concat_deepling,
    _download_intro_outro,
    _soften,
)
from .config import (
    _build_voice_map,
    read_env,
    resolve_llm_config,
    resolve_tts_config,
)
from .llm import call_llm
from .prompts import STAGE_FILES, STAGE_SYSTEMS, STAGE_TEMPERATURES
from .text_utils import (
    _extract_explicit_emotion,
    _extract_timing_hints,
    _infer_overlap_ms,
    _infer_tts_emotion,
    _remove_nonspoken_hints,
    parse_script,
)
from .tts import minimax_tts


# --- Feature 1: Text → Script ---

def generate_script(source_text: str, output_dir: Path, *,
                    llm_config: dict[str, str] | None = None,
                    log_fn=None) -> dict:
    """
    Run 4-stage LLM pipeline: source text → optimized podcast script.

    Returns dict with keys: final_script, stages[list of {name, path, chars}], output_dir.
    Intermediate files are written to output_dir (01-draft.md ... 04-final.md).
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
        temperature = STAGE_TEMPERATURES[i] if i < len(STAGE_TEMPERATURES) else 0.55
        result = call_llm(system, prefix + current,
                          llm_config["model"],
                          llm_config["api_key"], llm_config["base_url"],
                          temperature=temperature)
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
                 emotion_mode: str = "auto",
                 default_emotion: str | None = None,
                 natural_timing: bool = True,
                 auto_overlap: bool = True,
                 log_fn=None) -> dict:
    """
    Render a podcast script to MP3 audio.

    Natural timing notes:
    - time.sleep() below is only API throttling; it is NOT inserted into the audio.
    - The audio timeline can overlap turns using [[interrupt=420]] / [[overlap=260]].
    - When a speaker is interrupted, the previous segment's tail is automatically ducked.

    Returns dict with keys: raw_path, soft_path, deepling_path, segments, segment_emotions, segment_timing.
    """
    if tts_config is None:
        tts_config = resolve_tts_config()
    if env is None:
        env = read_env()

    items = parse_script(script_text)
    if not items:
        raise ValueError("No dialogue lines found in script")

    output_dir.mkdir(parents=True, exist_ok=True)
    seg_dir = output_dir / "segments"
    seg_dir.mkdir(parents=True, exist_ok=True)

    seg_soft_dir = output_dir / "segments-soft" if soft_edges else None
    if seg_soft_dir:
        seg_soft_dir.mkdir(parents=True, exist_ok=True)

    raw_files: list[Path] = []
    soft_files: list[Path] = []
    segment_emotions: list[dict[str, str]] = []
    segment_timing: list[dict] = []

    voice_map = _build_voice_map(env)
    tts_default_emotion = default_emotion or env.get("MINIMAX_TTS_DEFAULT_EMOTION") or "fluent"
    api_sleep = float(env.get("MINIMAX_TTS_API_SLEEP", "1.2"))

    prev_speaker: str | None = None
    prev_original_text = ""

    for idx, (speaker, original_text) in enumerate(items, 1):
        total = len(items)
        timing_hints, no_timing_text = _extract_timing_hints(original_text)
        explicit_overlap = timing_hints["overlap_ms"] > 0

        if auto_overlap and not explicit_overlap:
            timing_hints["overlap_ms"] = _infer_overlap_ms(
                prev_speaker, speaker, prev_original_text, no_timing_text, idx, total, env
            )

        voice_id = voice_map.get(speaker, env.get("MINIMAX_TTS_VOICE_ID", "Chinese (Mandarin)_Warm_Bestie"))
        raw_path = seg_dir / f"{idx:02d}-{speaker}.mp3"
        meta_path = seg_dir / f"{idx:02d}-{speaker}.json"

        if emotion_mode == "none":
            emo, tts_text = "", _extract_explicit_emotion(no_timing_text)[1]
        elif emotion_mode == "default":
            emo, tts_text = tts_default_emotion, _extract_explicit_emotion(no_timing_text)[1]
        else:
            emo, tts_text = _infer_tts_emotion(speaker, no_timing_text, env, default=tts_default_emotion)

        tts_text = _remove_nonspoken_hints(tts_text)

        cache_meta = {
            "speaker": speaker,
            "text": tts_text,
            "voice_id": voice_id,
            "emotion": emo,
            "model": tts_config["model"],
        }
        old_meta = None
        if meta_path.exists():
            try:
                old_meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                old_meta = None
        needs_tts = (
            force_tts
            or not raw_path.exists()
            or raw_path.stat().st_size == 0
            or old_meta != cache_meta
        )

        seg_meta = {
            "index": idx,
            "speaker": speaker,
            "emotion": emo,
            "overlap_ms": int(timing_hints.get("overlap_ms") or 0),
            "gap_ms": int(timing_hints.get("gap_ms") or 0),
            "text": tts_text,
        }
        segment_timing.append(seg_meta)
        segment_emotions.append({"index": str(idx), "speaker": speaker, "emotion": emo})

        if log_fn:
            snippet = tts_text[:60] + ("..." if len(tts_text) > 60 else "")
            emo_label = f" [{emo}]" if emo else ""
            timing_label = ""
            if seg_meta["overlap_ms"]:
                timing_label += f" overlap={seg_meta['overlap_ms']}ms"
            if seg_meta["gap_ms"]:
                timing_label += f" gap={seg_meta['gap_ms']}ms"
            cache_label = " regenerate" if needs_tts else " cached"
            log_fn(f"  {idx:02d}/{len(items):02d} {speaker}{emo_label}{timing_label}{cache_label}: {snippet}")

        if needs_tts:
            raw_path.write_bytes(minimax_tts(
                tts_config["api_key"], tts_config["base_url"], tts_config["model"],
                tts_text, voice_id, emotion=emo, fallback_emotion=tts_default_emotion))
            meta_path.write_text(json.dumps(cache_meta, ensure_ascii=False, indent=2), encoding="utf-8")
            if api_sleep > 0:
                time.sleep(api_sleep)
        raw_files.append(raw_path)

        if seg_soft_dir:
            soft_path = seg_soft_dir / f"{idx:02d}-{speaker}.mp3"
            if needs_tts or force_tts or not soft_path.exists() or soft_path.stat().st_size == 0:
                _soften(raw_path, soft_path)
            soft_files.append(soft_path)

        prev_speaker = speaker
        prev_original_text = original_text

    # assemble
    raw_final = output_dir / "final_raw.mp3"
    _assemble_dialogue_timeline(raw_files, segment_timing, raw_final, env, natural_timing=natural_timing)

    soft_final = output_dir / "final_soft.mp3" if soft_files else None
    if soft_files:
        _assemble_dialogue_timeline(soft_files, segment_timing, soft_final, env, natural_timing=natural_timing)

    deepling_final = output_dir / "final_deepling.mp3" if deepling_branding else None
    if deepling_branding:
        intro_p, outro_p = _download_intro_outro(output_dir)
        dialogue_p = output_dir / "final_dialogue.mp3"
        dialogue_source = soft_files if soft_files else raw_files
        _assemble_dialogue_timeline(dialogue_source, segment_timing, dialogue_p, env, natural_timing=natural_timing)
        _concat_deepling(intro_p, dialogue_p, outro_p, deepling_final)

    timing_path = output_dir / "segment_timing.json"
    timing_path.write_text(json.dumps(segment_timing, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "raw_path": str(raw_final),
        "soft_path": str(soft_final) if soft_final else None,
        "deepling_path": str(deepling_final) if deepling_final else None,
        "segments": [str(p) for p in raw_files],
        "segment_emotions": segment_emotions,
        "segment_timing": segment_timing,
        "timing_path": str(timing_path),
        "line_count": len(items),
    }
