"""
Companion-File-Handling: Automatische Extraktion von Container-SRT und Thumbnail-Generierung.
Nutzt ffmpeg/ffprobe für Video-Operationen.
"""

import subprocess
import shutil
from pathlib import Path
from typing import Tuple, Optional, List


def check_ffmpeg_available() -> Tuple[bool, str]:
    """
    Prüft ob ffmpeg und ffprobe verfügbar sind.

    Returns:
        (verfügbar: bool, fehlermeldung: str)
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            return False, "ffmpeg nicht ausführbar"

        result = subprocess.run(
            ["ffprobe", "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            return False, "ffprobe nicht ausführbar"

        return True, ""

    except FileNotFoundError:
        return False, "ffmpeg/ffprobe nicht im PATH gefunden"
    except Exception as e:
        return False, f"Fehler beim Prüfen: {str(e)}"


def find_subtitle_streams(video_path: str) -> Tuple[bool, List[int], str]:
    """
    Findet Untertitel-Streams im Container.

    Args:
        video_path: Pfad zur Video-Datei

    Returns:
        (erfolg: bool, stream_indices: List[int], fehlermeldung: str)
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-select_streams", "s",
                "-show_entries", "stream=index",
                "-of", "csv=p=0",
                video_path
            ],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return False, [], f"ffprobe Fehler: {result.stderr}"

        # Parse Stream-Indices
        indices = []
        for line in result.stdout.strip().split('\n'):
            if line:
                try:
                    indices.append(int(line))
                except ValueError:
                    continue

        return True, indices, ""

    except Exception as e:
        return False, [], f"Fehler: {str(e)}"


def extract_subtitle_stream(
    video_path: str,
    stream_index: int,
    output_path: Optional[str] = None
) -> Tuple[bool, str, str]:
    """
    Extrahiert Untertitel-Stream aus Container.

    Args:
        video_path: Pfad zur Video-Datei
        stream_index: Stream-Index (absoluter Index von ffprobe)
        output_path: Optional, Ausgabepfad (default: <video_basename>.srt)

    Returns:
        (erfolg: bool, output_path: str, fehlermeldung: str)
    """
    video_path_obj = Path(video_path)

    if output_path is None:
        output_path = str(video_path_obj.parent / f"{video_path_obj.stem}.srt")

    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",  # Überschreibe existierende Datei
                "-nostdin",  # Keine interaktive Eingabe
                "-i", video_path,
                "-map", f"0:{stream_index}",  # Nutze absoluten Stream-Index
                output_path
            ],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return False, "", f"ffmpeg Fehler: {result.stderr}"

        # Prüfe ob Datei erstellt wurde
        if not Path(output_path).exists():
            return False, "", "Ausgabedatei nicht erstellt"

        return True, output_path, ""

    except Exception as e:
        return False, "", f"Fehler: {str(e)}"


def generate_thumbnail(
    video_path: str,
    time_seconds: int = 3,
    output_path: Optional[str] = None
) -> Tuple[bool, str, str]:
    """
    Generiert Thumbnail aus Video bei bestimmter Zeit.

    Args:
        video_path: Pfad zur Video-Datei
        time_seconds: Zeitpunkt für Screenshot (Standard: 3s)
        output_path: Optional, Ausgabepfad (default: <video_basename>_thumb.jpg)

    Returns:
        (erfolg: bool, output_path: str, fehlermeldung: str)
    """
    video_path_obj = Path(video_path)

    if output_path is None:
        output_path = str(video_path_obj.parent / f"{video_path_obj.stem}_thumb.jpg")

    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",  # Überschreibe existierende Datei
                "-nostdin",
                "-ss", str(time_seconds),  # Seek zu Zeit
                "-i", video_path,
                "-frames:v", "1",  # Nur 1 Frame
                "-q:v", "2",  # Qualität (2 = sehr gut)
                output_path
            ],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return False, "", f"ffmpeg Fehler: {result.stderr}"

        # Prüfe ob Datei erstellt wurde
        if not Path(output_path).exists():
            return False, "", "Thumbnail nicht erstellt"

        return True, output_path, ""

    except Exception as e:
        return False, "", f"Fehler: {str(e)}"


def get_video_companion_files(video_path: str) -> dict:
    """
    Findet alle Companion-Dateien für ein Video basierend auf neuen Namenskonventionen.

    Sucht nach:
    - *_yt_profile.json (YouTube-Metadaten)
    - *_softsubs.mp4 (Video mit Container-SRT)
    - *_hardsubs.mp4 (Video mit eingebrannten Untertiteln)
    - *.srt (externe Untertitel)
    - sample_*.png (Thumbnail nach Textanimation)

    Args:
        video_path: Pfad zur Video-Datei

    Returns:
        dict mit Keys:
            - json_file: str oder None
            - softsubs_file: str oder None
            - hardsubs_file: str oder None
            - srt_file: str oder None
            - thumbnail_file: str oder None
    """
    from app.matching import (
        find_yt_profile_json,
        find_specialized_video_files,
        find_sample_thumbnail,
        find_all_matching_files
    )
    from app.config import SUPPORTED_SUB_EXTS

    video_dir = Path(video_path).parent
    result = {
        "json_file": None,
        "softsubs_file": None,
        "hardsubs_file": None,
        "srt_file": None,
        "thumbnail_file": None
    }

    # Suche JSON
    result["json_file"] = find_yt_profile_json(video_path)

    # Suche Video-Varianten
    video_variants = find_specialized_video_files(video_path)
    result["softsubs_file"] = video_variants.get("softsubs_file")
    result["hardsubs_file"] = video_variants.get("hardsubs_file")

    # Suche externe SRT (mit Präfix-Matching)
    srt_files = find_all_matching_files(video_path, SUPPORTED_SUB_EXTS, prefix_len=12)
    if srt_files:
        result["srt_file"] = srt_files[0]  # Nimm erste gefundene

    # Suche Thumbnail
    result["thumbnail_file"] = find_sample_thumbnail(video_path)

    return result
