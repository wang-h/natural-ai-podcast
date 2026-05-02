#!/usr/bin/env python3
"""
natural-ai-podcast web API
  1. GET /api/runs   -> List all podcasts
  2. POST /api/script -> Generate script
  3. POST /api/render -> Render audio
"""

from __future__ import annotations

import json
import re
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent))
from podcast_engine import (
    generate_script,
    render_audio,
    parse_script,
    read_env,
    resolve_llm_config,
    resolve_tts_config,
    STAGE_FILES,
)

PROJECT_DIR = Path(__file__).resolve().parent
RUNS_DIR = PROJECT_DIR / "runs"
FRONTEND_DIST = PROJECT_DIR / "frontend" / "dist"

RUNS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="natural-ai-podcast-api")

# 1. Mount audio files
app.mount("/runs", StaticFiles(directory=str(RUNS_DIR)), name="runs")

# 2. Mount Astro's internal static assets directory if it exists
ASTRO_ASSETS = FRONTEND_DIST / "_astro"
if ASTRO_ASSETS.exists():
    app.mount("/_astro", StaticFiles(directory=str(ASTRO_ASSETS)), name="astro_assets")

# API Endpoints
@app.get("/api/runs")
async def list_runs():
    results = []
    for d in sorted(RUNS_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if not d.is_dir():
            continue
        final_md = d / "04-final.md"
        if not final_md.exists():
            continue
        
        deepling = d / "final_deepling.mp3"
        raw = d / "final_raw.mp3"
        ext_url_file = d / "audio_url.txt"

        audio_url = None
        if ext_url_file.exists():
            audio_url = ext_url_file.read_text(encoding="utf-8").strip()
        
        if not audio_url:
            for cand in (deepling, raw):
                if cand.exists() and cand.stat().st_size > 0:
                    audio_url = f"/runs/{d.name}/{cand.name}"
                    break

        script = final_md.read_text(encoding="utf-8")
        lines = parse_script(script)
        
        # Format lines for frontend
        formatted_lines = [{"speaker": sp, "text": txt} for sp, txt in lines]
        
        preview_line = ""
        for sp, txt in lines:
            if "大家好" not in txt and "欢迎收听" not in txt:
                preview_line = txt[:100]
                break

        results.append({
            "id": d.name,
            "created": datetime.fromtimestamp(d.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%d %H:%M"),
            "preview": preview_line,
            "lines": formatted_lines[:6],  # Only show first 6 lines on home page for better spacing
            "audio_url": audio_url,
            "has_deepling": deepling.exists(),
            "line_count": len(lines),
        })
    return JSONResponse(content=results)

@app.get("/api/runs/{run_id}")
async def run_detail(run_id: str):
    run_dir = RUNS_DIR / run_id
    if not run_dir.is_dir():
        raise HTTPException(status_code=404, detail="Run not found")

    final_md = run_dir / "04-final.md"
    script_text = final_md.read_text(encoding="utf-8") if final_md.exists() else ""
    lines = [{"speaker": sp, "text": txt} for sp, txt in parse_script(script_text)]

    audio_url = None
    ext_url_file = run_dir / "audio_url.txt"
    if ext_url_file.exists():
        audio_url = ext_url_file.read_text(encoding="utf-8").strip()
    else:
        for fname in ("final_deepling.mp3", "final_raw.mp3"):
            if (run_dir / fname).exists():
                audio_url = f"/runs/{run_id}/{fname}"
                break

    stages = []
    for fname in STAGE_FILES:
        fp = run_dir / fname
        if fp.exists():
            txt = fp.read_text(encoding="utf-8")
            stages.append({"name": fname, "chars": len(txt), "preview": txt[:600]})

    return JSONResponse(content={
        "id": run_id,
        "script_text": script_text,
        "lines": lines,
        "audio_url": audio_url,
        "stages": stages
    })

class ScriptRequest(BaseModel):
    source: str
    model: str = ""

@app.post("/api/script")
async def api_script_generate(req: ScriptRequest):
    env = read_env()
    llm = resolve_llm_config(env)
    if req.model.strip():
        llm["model"] = req.model.strip()

    run_name = f"script-{int(time.time())}"
    run_dir = RUNS_DIR / run_name
    source_text = req.source.strip()
    
    if not source_text:
        default_src = PROJECT_DIR.parent / "podcast-edge-samples" / "goblin-only-v7.md"
        if default_src.exists():
            source_text = default_src.read_text(encoding="utf-8")
        else:
            raise HTTPException(status_code=400, detail="No source text provided")

    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "source.md").write_text(source_text, encoding="utf-8")

    logs = []
    def log(msg: str): logs.append(msg)

    try:
        result = generate_script(source_text, run_dir, llm_config=llm, log_fn=log)
        return JSONResponse(content={
            "success": True,
            "run_id": run_name,
            "script": result["final_script"],
            "stages": [dict(s) for s in result["stages"]],
            "log": "\n".join(logs)
        })
    except Exception as exc:
        return JSONResponse(content={"success": False, "error": str(exc), "log": "\n".join(logs)}, status_code=500)

class RenderRequest(BaseModel):
    script: str
    run_id: str = ""
    soft: bool = True
    branding: bool = True
    force: bool = False

@app.post("/api/render")
async def api_render_episode(req: RenderRequest):
    env = read_env()
    tts = resolve_tts_config(env)

    script_text = req.script.strip()
    if not script_text and req.run_id.strip():
        md = RUNS_DIR / req.run_id.strip() / "04-final.md"
        if md.exists():
            script_text = md.read_text(encoding="utf-8")

    if not script_text:
        raise HTTPException(status_code=400, detail="No script provided")

    out_name = req.run_id.strip() if req.run_id.strip() else f"render-{int(time.time())}"
    run_dir = RUNS_DIR / out_name
    run_dir.mkdir(parents=True, exist_ok=True)

    final_md = run_dir / "04-final.md"
    if not final_md.exists():
        final_md.write_text(script_text, encoding="utf-8")

    logs = []
    def log(msg: str): logs.append(msg)

    try:
        result = render_audio(script_text, run_dir, tts_config=tts, env=env,
                              soft_edges=req.soft, deepling_branding=req.branding,
                              force_tts=req.force, log_fn=log)
        
        audio_info = {}
        for key, path_str in [("raw", result["raw_path"]), ("soft", result["soft_path"]), ("deepling", result["deepling_path"])]:
            if path_str:
                p = Path(path_str)
                if p.exists():
                    audio_info[key] = {"url": f"/runs/{out_name}/{p.name}", "size": f"{p.stat().st_size / 1024:.0f} KB"}
                    
        return JSONResponse(content={
            "success": True,
            "run_id": out_name,
            "audio": audio_info,
            "line_count": result["line_count"],
            "log": "\n".join(logs)
        })
    except Exception as exc:
        return JSONResponse(content={"success": False, "error": str(exc), "log": "\n".join(logs)}, status_code=500)

# Serve Frontend Pages & Static Assets
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    if not FRONTEND_DIST.exists():
        return JSONResponse({"message": "Frontend not built. Run 'npm run build' in frontend directory."}, status_code=404)

    # Clean up the path
    clean_path = full_path.strip("/")

    # 1. Try to serve the exact file (e.g. css, js, icons)
    file_path = FRONTEND_DIST / full_path
    if file_path.is_file():
        return FileResponse(file_path)

    # 2. Try directory mapping (e.g. /script -> /script/index.html)
    # Check both original and cleaned path
    for p in [full_path, clean_path]:
        if not p: continue
        dir_index = FRONTEND_DIST / p / "index.html"
        if dir_index.is_file():
            return FileResponse(dir_index)

    # 3. Special case for root-level pages built by Astro
    if clean_path:
        root_page = FRONTEND_DIST / f"{clean_path}.html"
        if root_page.is_file():
            return FileResponse(root_page)

    # 4. Fallback to root index.html
    return FileResponse(FRONTEND_DIST / "index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8700, reload=True)
