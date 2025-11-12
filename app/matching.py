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
    SUPPORTED_INFO_EXTS
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
