"""
podcast_engine — core functions for natural podcast generation.

Two main capabilities:
  1. generate_script() — any text → optimized podcast script (4-stage LLM pipeline)
  2. render_audio()   — podcast script → natural MP3 (MiniMax TTS + Deepling branding)

All state lives under output_dir; intermediate files are preserved for inspection.
"""

from .config import read_env, resolve_llm_config, resolve_tts_config
from .core import generate_script, render_audio
from .prompts import STAGE_FILES
from .text_utils import parse_script

__all__ = [
    "generate_script",
    "render_audio",
    "parse_script",
    "read_env",
    "resolve_llm_config",
    "resolve_tts_config",
    "STAGE_FILES",
]
