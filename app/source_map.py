"""
Persistent mapping between YouTube video IDs and local source directories.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_MAP_FILE = REPO_ROOT / ".config/source_map.json"


def load_source_map() -> dict:
    if not SOURCE_MAP_FILE.exists():
        return {}
    try:
        with SOURCE_MAP_FILE.open("r", encoding="utf-8") as infile:
            return json.load(infile)
    except Exception:
        return {}


def save_source_map(mapping: dict) -> None:
    SOURCE_MAP_FILE.parent.mkdir(parents=True, exist_ok=True)
    with SOURCE_MAP_FILE.open("w", encoding="utf-8") as outfile:
        json.dump(mapping, outfile, indent=2)


def update_source_folder(video_id: str, folder_path: str) -> None:
    if not video_id or not folder_path:
        return
    mapping = load_source_map()
    mapping[video_id] = folder_path
    save_source_map(mapping)


def get_source_folder(video_id: str) -> Optional[str]:
    mapping = load_source_map()
    return mapping.get(video_id)
