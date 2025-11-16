"""
Logik zur automatischen Suche passender Dateien (SRT, JSON) basierend auf Namenspräfix.
Implementiert präzises Matching mit Auswahl-Option bei Mehrdeutigkeiten.
"""

import os
from pathlib import Path
from typing import Optional, Tuple, List
from app.config import (
    DEFAULT_PREFIX_LEN,
    SUPPORTED_SUB_EXTS,
    SUPPORTED_INFO_EXTS,
    SUPPORTED_THUMB_EXTS
)


class FileMatchingError(Exception):
    """Fehler bei der Dateisuche."""
    pass


def get_file_prefix(file_path: str, prefix_len: int = DEFAULT_PREFIX_LEN) -> str:
    """
    Extrahiert Präfix aus Dateinamen (ohne Extension).

    Args:
        file_path: Pfad zur Datei
        prefix_len: Länge des Präfix (Default: 12)

    Returns:
        Präfix-String
    """
    file_name = Path(file_path).stem  # Dateiname ohne Extension
    return file_name[:prefix_len]


def find_matching_file(video_path: str, extensions: list[str], prefix_len: int = DEFAULT_PREFIX_LEN) -> Optional[str]:
    """
    Sucht passende Datei im selben Verzeichnis basierend auf Namenspräfix.

    Args:
        video_path: Pfad zur Video-Datei
        extensions: Liste erlaubter Extensions (z.B. [".srt"])
        prefix_len: Länge des Präfix für Matching

    Returns:
        Pfad zur gefundenen Datei oder None

    Raises:
        FileMatchingError: Bei Mehrfachtreffern oder Datei-Fehlern
    """
    video_dir = Path(video_path).parent
    video_prefix = get_file_prefix(video_path, prefix_len)

    # Suche alle Dateien mit passenden Extensions
    matches = []
    for ext in extensions:
        pattern = f"{video_prefix}*{ext}"
        found_files = list(video_dir.glob(pattern))
        matches.extend(found_files)

    if len(matches) == 0:
        return None
    elif len(matches) == 1:
        return str(matches[0])
    else:
        # Mehrfachtreffer → Fail Fast
        match_names = [m.name for m in matches]
        raise FileMatchingError(
            f"Mehrdeutiger Match für Präfix '{video_prefix}*':\n"
            f"Gefundene Dateien: {', '.join(match_names)}\n"
            f"Bitte eindeutige Dateinamen verwenden."
        )


def find_all_matching_files(video_path: str, extensions: list[str], prefix_len: int = DEFAULT_PREFIX_LEN) -> List[str]:
    """
    Sucht ALLE passenden Dateien im selben Verzeichnis basierend auf Namenspräfix.

    Args:
        video_path: Pfad zur Video-Datei
        extensions: Liste erlaubter Extensions (z.B. [".srt"])
        prefix_len: Länge des Präfix für Matching

    Returns:
        Liste mit Pfaden zu allen gefundenen Dateien (kann leer sein)
    """
    video_dir = Path(video_path).parent
    video_prefix = get_file_prefix(video_path, prefix_len)

    # Suche alle Dateien mit passenden Extensions
    matches = []
    for ext in extensions:
        pattern = f"{video_prefix}*{ext}"
        found_files = list(video_dir.glob(pattern))
        matches.extend(found_files)

    matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return [str(m) for m in matches]


def find_companion_files(video_path: str, prefix_len: int = DEFAULT_PREFIX_LEN) -> Tuple[Optional[str], Optional[str]]:
    """
    Findet passende SRT- und JSON-Dateien für ein Video.

    Args:
        video_path: Pfad zur Video-Datei
        prefix_len: Länge des Präfix für Matching

    Returns:
        Tuple (srt_path, json_path)
        - Beide können None sein, wenn nicht gefunden

    Raises:
        FileMatchingError: Bei Mehrfachtreffern
    """
    srt_path = find_matching_file(video_path, SUPPORTED_SUB_EXTS, prefix_len)
    json_path = find_matching_file(video_path, SUPPORTED_INFO_EXTS, prefix_len)

    return srt_path, json_path


def find_companion_files_multi(video_path: str, prefix_len: int = DEFAULT_PREFIX_LEN) -> Tuple[List[str], List[str]]:
    """
    Findet ALLE passenden SRT- und JSON-Dateien für ein Video.
    Wirft keine Exception bei Mehrfachtreffern, sondern gibt alle zurück.

    Args:
        video_path: Pfad zur Video-Datei
        prefix_len: Länge des Präfix für Matching

    Returns:
        Tuple (srt_files, json_files)
        - Beide sind Listen, können leer sein
    """
    srt_files = find_all_matching_files(video_path, SUPPORTED_SUB_EXTS, prefix_len)
    json_files = find_all_matching_files(video_path, SUPPORTED_INFO_EXTS, prefix_len)

    return srt_files, json_files


def _extract_base_name(video_stem: str) -> str:
    """
    Extrahiert Basis-Namen aus Video-Dateiname durch Entfernen bekannter Suffixe und Zeitstempel.

    Args:
        video_stem: Dateiname ohne Extension

    Returns:
        Basis-Name ohne Suffixe und Zeitstempel
    """
    import re

    base_name = video_stem

    # Entferne zuerst Zeitstempel, dann Suffixe
    # (da Zeitstempel zwischen Suffixen liegen kann)

    # Schritt 1: Entferne alle bekannten Suffixe iterativ
    while True:
        removed = False
        for suffix in ["_softsubs", "_hardsubs", "_podcast"]:
            if base_name.endswith(suffix):
                base_name = base_name[:-(len(suffix))]
                removed = True
                break
        if not removed:
            break

    # Schritt 2: Entferne Zeitstempel-Pattern (z.B. _20251103_085932)
    base_name = re.sub(r'_\d{8}_\d{6}$', '', base_name)

    # Schritt 3: Nochmal Suffixe entfernen (falls Zeitstempel zwischen Suffix und Basis war)
    while True:
        removed = False
        for suffix in ["_softsubs", "_hardsubs", "_podcast"]:
            if base_name.endswith(suffix):
                base_name = base_name[:-(len(suffix))]
                removed = True
                break
        if not removed:
            break

    return base_name


def find_specialized_video_files(video_path: str) -> dict:
    """
    Findet spezialisierte Video-Varianten basierend auf Namenskonventionen.

    Sucht nach:
    - *_softsubs.mp4 (Video mit Container-Untertiteln)
    - *_hardsubs.mp4 (Video mit eingebrannten Untertiteln)

    Args:
        video_path: Pfad zur Video-Datei (beliebige Variante)

    Returns:
        dict mit Keys: softsubs_file, hardsubs_file (jeweils str oder None)
    """
    video_dir = Path(video_path).parent
    video_stem = Path(video_path).stem

    # Extrahiere Basis-Namen
    base_name = _extract_base_name(video_stem)

    # Suche nach spezialisierten Varianten
    def _find_newest(patterns):
        candidates = []
        for pattern in patterns:
            candidates.extend(video_dir.glob(pattern))
        if not candidates:
            return None
        newest = max(candidates, key=lambda p: p.stat().st_mtime)
        return str(newest)

    return {
        "softsubs_file": _find_newest([
            f"{base_name}_softsubs.mp4",
            f"{base_name}*_softsubs.mp4"
        ]),
        "hardsubs_file": _find_newest([
            f"{base_name}_hardsubs.mp4",
            f"{base_name}*_hardsubs.mp4"
        ])
    }


def find_yt_profile_json(video_path: str) -> Optional[str]:
    """
    Sucht nach YouTube-Profil-JSON mit Namenskonvention *_yt_profile.json.

    Args:
        video_path: Pfad zur Video-Datei

    Returns:
        Pfad zur JSON-Datei oder None
    """
    video_dir = Path(video_path).parent
    # Suche nach Dateien, die nur auf *_yt_profile.json enden (Suffix reicht)
    pattern = "*_yt_profile.json"
    matches = list(video_dir.glob(pattern))

    if matches:
        newest = max(matches, key=lambda p: p.stat().st_mtime)
        return str(newest)

    return None


def find_sample_thumbnail(video_path: str) -> Optional[str]:
    """
    Sucht nach Thumbnail-Dateien im selben Verzeichnis.

    Patterns:
    - *_thumbnail.png (bevorzugt, matches video basename)
    - sample_*.png (alternative)

    Args:
        video_path: Pfad zur Video-Datei

    Returns:
        Pfad zum Thumbnail oder None
    """
    video_dir = Path(video_path).parent
    video_stem = Path(video_path).stem

    # Extrahiere Basis-Namen
    base_name = _extract_base_name(video_stem)

    candidate_files = []

    # Pattern 1: <basename>*_thumbnail.<ext>
    for ext in SUPPORTED_THUMB_EXTS:
        candidate_files.extend(video_dir.glob(f"{base_name}*_thumbnail{ext}"))

    # Pattern 2: <basename>*_thumb.<ext> (z.B. *_softsubs_thumb.jpg)
    for ext in SUPPORTED_THUMB_EXTS:
        candidate_files.extend(video_dir.glob(f"{base_name}*_thumb{ext}"))

    if candidate_files:
        newest = max(candidate_files, key=lambda p: p.stat().st_mtime)
        return str(newest)

    # Pattern 3: sample_*.<ext> (Fallback)
    fallback_candidates = []
    for ext in SUPPORTED_THUMB_EXTS:
        fallback_candidates.extend(video_dir.glob(f"sample_*{ext}"))

    if fallback_candidates:
        newest = max(fallback_candidates, key=lambda p: p.stat().st_mtime)
        return str(newest)

    return None


def validate_video_file(video_path: str) -> Tuple[bool, str]:
    """
    Validiert, ob Video-Datei existiert und lesbar ist.

    Args:
        video_path: Pfad zur Video-Datei

    Returns:
        Tuple (is_valid, error_message)
    """
    if not video_path:
        return False, "Kein Video ausgewählt."

    video_file = Path(video_path)

    if not video_file.exists():
        return False, f"Datei nicht gefunden: {video_path}"

    if not video_file.is_file():
        return False, f"Pfad ist keine Datei: {video_path}"

    if not os.access(video_path, os.R_OK):
        return False, f"Datei nicht lesbar: {video_path}"

    return True, ""
