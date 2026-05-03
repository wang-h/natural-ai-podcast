#!/usr/bin/env python3
"""
Pre-generate static JSON data from runs/ directory for GitHub Pages deployment.

Usage:
    python scripts/build-static-data.py

This scans runs/ and creates:
    frontend/public/static-data/runs.json          — episode list
    frontend/public/static-data/runs/{id}.json      — per-episode detail
    frontend/public/static-data/audio/              — symlinks to mp3 files
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
RUNS_DIR = PROJECT_DIR / "runs"
OUTPUT_DIR = PROJECT_DIR / "frontend" / "public" / "static-data"
RUNS_OUTPUT = OUTPUT_DIR / "runs"
AUDIO_OUTPUT = OUTPUT_DIR / "audio"

sys_path_hack = str(PROJECT_DIR)


def parse_script(text: str) -> list[tuple[str, str]]:
    import re
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


def main():
    import sys
    sys.path.insert(0, sys_path_hack)

    RUNS_OUTPUT.mkdir(parents=True, exist_ok=True)
    AUDIO_OUTPUT.mkdir(parents=True, exist_ok=True)

    episodes = []

    for d in sorted(RUNS_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if not d.is_dir():
            continue
        final_md = d / "04-final.md"
        if not final_md.exists():
            continue

        deepling = d / "final_deepling.mp3"
        raw = d / "final_raw.mp3"

        audio_filename = None
        for cand in (deepling, raw):
            if cand.exists() and cand.stat().st_size > 0:
                audio_filename = cand.name
                break

        if audio_filename:
            src = d / audio_filename
            dst = AUDIO_OUTPUT / f"{d.name}.mp3"
            shutil.copy2(src, dst)

        script = final_md.read_text(encoding="utf-8")
        lines = parse_script(script)

        preview_line = ""
        for sp, txt in lines:
            if "大家好" not in txt and "欢迎收听" not in txt:
                preview_line = txt[:100]
                break

        audio_url = f"/static-data/audio/{d.name}.mp3" if audio_filename else None

        episode = {
            "id": d.name,
            "created": datetime.fromtimestamp(d.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%d %H:%M"),
            "preview": preview_line,
            "lines": [{"speaker": sp, "text": txt} for sp, txt in lines[:6]],
            "audio_url": audio_url,
            "has_deepling": deepling.exists(),
            "line_count": len(lines),
        }
        episodes.append(episode)

        detail = {
            "id": d.name,
            "script_text": script,
            "lines": [{"speaker": sp, "text": txt} for sp, txt in lines],
            "audio_url": audio_url,
            "stages": [],
        }
        for fname in ["01-draft.md", "02-director.md", "03-performance.md", "04-final.md"]:
            fp = d / fname
            if fp.exists():
                txt = fp.read_text(encoding="utf-8")
                detail["stages"].append({"name": fname, "chars": len(txt), "preview": txt[:600]})

        (RUNS_OUTPUT / f"{d.name}.json").write_text(
            json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    runs_json = OUTPUT_DIR / "runs.json"
    runs_json.write_text(json.dumps(episodes, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Generated {len(episodes)} episodes")
    print(f"  runs.json -> {runs_json}")
    print(f"  details  -> {RUNS_OUTPUT}/")
    print(f"  audio    -> {AUDIO_OUTPUT}/")


if __name__ == "__main__":
    main()
