"""
Favoriten-Verzeichnisse für schnellen Zugriff.
Speichert/lädt Liste von häufig genutzten Pfaden.
"""

import json
from pathlib import Path
from typing import List, Optional


DEFAULT_CONFIG_DIR = Path.home() / ".config" / "yt-upload"
DEFAULT_FAVORITES_FILE = DEFAULT_CONFIG_DIR / "favorite_dirs.json"
DEFAULT_PROFILE_PREFS_FILE = DEFAULT_CONFIG_DIR / "profile_prefs.json"


def load_favorites(config_path: Optional[Path] = None) -> List[dict]:
    """
    Lädt Favoriten-Verzeichnisse aus JSON.

    Returns:
        Liste von Dicts mit Keys: "label", "path"
        Fallback auf leere Liste wenn Datei nicht existiert.
    """
    if config_path is None:
        config_path = DEFAULT_FAVORITES_FILE

    if not config_path.exists():
        return []

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            favorites = json.load(f)

        # Validierung
        if not isinstance(favorites, list):
            return []

        # Filtere gültige Einträge
        valid = []
        for fav in favorites:
            if isinstance(fav, dict) and "label" in fav and "path" in fav:
                valid.append(fav)

        return valid

    except Exception:
        return []


def save_favorites(favorites: List[dict], config_path: Optional[Path] = None) -> bool:
    """
    Speichert Favoriten-Verzeichnisse als JSON.

    Args:
        favorites: Liste von Dicts mit Keys: "label", "path"
        config_path: Optional, Pfad zur Config-Datei

    Returns:
        True bei Erfolg, False bei Fehler
    """
    if config_path is None:
        config_path = DEFAULT_FAVORITES_FILE

    # Erstelle Verzeichnis falls nötig
    config_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(favorites, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def add_favorite(label: str, path: str, config_path: Optional[Path] = None) -> bool:
    """
    Fügt neuen Favoriten hinzu (oder aktualisiert existierenden).

    Args:
        label: Anzeigename für Button
        path: Verzeichnispfad
        config_path: Optional, Pfad zur Config-Datei

    Returns:
        True bei Erfolg, False bei Fehler
    """
    favorites = load_favorites(config_path)

    # Prüfe ob Label bereits existiert → Update
    found = False
    for fav in favorites:
        if fav["label"] == label:
            fav["path"] = path
            found = True
            break

    if not found:
        favorites.append({"label": label, "path": path})

    return save_favorites(favorites, config_path)


def remove_favorite(label: str, config_path: Optional[Path] = None) -> bool:
    """
    Entfernt Favoriten anhand Label.

    Args:
        label: Anzeigename des zu entfernenden Favoriten
        config_path: Optional, Pfad zur Config-Datei

    Returns:
        True bei Erfolg, False bei Fehler
    """
    favorites = load_favorites(config_path)
    favorites = [f for f in favorites if f["label"] != label]
    return save_favorites(favorites, config_path)


def get_default_favorites() -> List[dict]:
    """
    Gibt Standard-Favoriten zurück (falls keine gespeichert).

    Returns:
        Liste von Standard-Verzeichnissen
    """
    home = Path.home()
    return [
        {"label": "■ Home", "path": str(home)},
        {"label": "■ Videos", "path": str(home / "Videos")},
        {"label": "■ Downloads", "path": str(home / "Downloads")},
    ]


def load_profile_preferences(config_path: Optional[Path] = None) -> dict:
    """
    Lädt gespeicherte Profil-Präferenzen (pro Video-Basename).

    Returns:
        Dict[video_basename, Dict[profile_name, bool]]
    """
    if config_path is None:
        config_path = DEFAULT_PROFILE_PREFS_FILE

    if not config_path.exists():
        return {}

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_profile_preferences(prefs: dict, config_path: Optional[Path] = None) -> bool:
    """
    Speichert Profil-Präferenzen.

    Args:
        prefs: Dict[video_basename, Dict[profile_name, bool]]
        config_path: Optional, Pfad zur Config-Datei

    Returns:
        True bei Erfolg, False bei Fehler
    """
    if config_path is None:
        config_path = DEFAULT_PROFILE_PREFS_FILE

    config_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(prefs, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False
