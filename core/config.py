import os
import json
from utils.theme import BLUE
from core.transcripts.models import (
    DEFAULT_TRANSCRIPT_LANGUAGES,
    DEFAULT_TRANSCRIPT_OUTPUT_FORMAT,
    DEFAULT_TRANSCRIPT_PROGRESS_INTERVAL,
)

SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".mediafetch_settings.json")
HISTORY_FILE  = os.path.join(os.path.expanduser("~"), ".mediafetch_history.json")

DEFAULT_SETTINGS = {
    "download_path":        os.path.join(os.path.expanduser("~"), "Downloads"),
    "default_quality":      "Best Quality",
    "default_format":       "mp4",
    "default_audio_quality":"192",
    "embed_subtitles":      False,
    "embed_thumbnail":      False,
    "embed_metadata":       True,
    "write_description":    False,
    "max_history":          50,
    "theme_accent":         BLUE,
    "concurrent_fragments": 4,
    "transcript_output_path": os.path.join(os.path.expanduser("~"), "Downloads", "Transcripts"),
    "transcript_languages": ",".join(DEFAULT_TRANSCRIPT_LANGUAGES),
    "transcript_output_format": DEFAULT_TRANSCRIPT_OUTPUT_FORMAT,
    "transcript_timestamps": False,
    "transcript_metadata_only": False,
    "transcript_auto_fallback": True,
    "transcript_manual_only": False,
    "transcript_keep_cues": False,
    "transcript_retries": 3,
    "transcript_retry_delay": 2.0,
    "transcript_progress_interval": DEFAULT_TRANSCRIPT_PROGRESS_INTERVAL,
    "transcript_delay": 0.5,
}

def load_settings() -> dict:
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("Settings file is not a JSON object")
        result = DEFAULT_SETTINGS.copy()
        for k, default_v in DEFAULT_SETTINGS.items():
            raw = data.get(k, default_v)
            if not isinstance(raw, type(default_v)):
                raw = default_v
            result[k] = raw
        return result
    except Exception:
        return DEFAULT_SETTINGS.copy()

def save_settings(s: dict):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def load_history() -> list:
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []

def save_history(h: list):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(h, f, indent=2, ensure_ascii=False)
    except Exception:
        pass
