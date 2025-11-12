"""
Laden und Validieren von Upload-Profilen aus YAML-Datei.
Jedes Profil enthält YouTube-Einstellungen und eine Beschreibung.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Tuple
from app.config import PROFILES_PATH


class ProfileError(Exception):
    """Fehler beim Laden oder Validieren von Profilen."""
    pass


def load_profiles(profile_path: str = PROFILES_PATH) -> Dict[str, Any]:
    """
    Lädt Upload-Profile aus YAML-Datei.

    Args:
        profile_path: Pfad zur profiles.yaml

    Returns:
        Dictionary mit Profilen (key = Profilname, value = Profil-Daten)

    Raises:
        ProfileError: Bei Fehlern beim Laden
    """
    file_path = Path(profile_path)

    if not file_path.exists():
        raise ProfileError(f"Profil-Datei nicht gefunden: {profile_path}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            profiles = yaml.safe_load(f)

        if not profiles:
            raise ProfileError(f"Keine Profile in {profile_path} gefunden.")

        if not isinstance(profiles, dict):
            raise ProfileError(f"Ungültiges Format in {profile_path}. Erwartet: Dictionary.")

        # Validiere jedes Profil
        for profile_name, profile_data in profiles.items():
            validate_profile(profile_name, profile_data)

        return profiles

    except yaml.YAMLError as e:
        raise ProfileError(f"YAML-Parsing-Fehler: {str(e)}")
    except Exception as e:
        raise ProfileError(f"Fehler beim Laden der Profile: {str(e)}")


def validate_profile(profile_name: str, profile_data: Dict[str, Any]) -> None:
    """
    Validiert Struktur eines Upload-Profils.

    Args:
        profile_name: Name des Profils
        profile_data: Profil-Daten

    Raises:
        ProfileError: Bei ungültiger Struktur
    """
    if not isinstance(profile_data, dict):
        raise ProfileError(f"Profil '{profile_name}' ist kein Dictionary.")

    # Beschreibung ist Pflicht
    if "description" not in profile_data:
        raise ProfileError(f"Profil '{profile_name}' fehlt 'description'.")

    if not isinstance(profile_data["description"], str):
        raise ProfileError(f"Profil '{profile_name}': 'description' muss String sein.")

    # Status-Sektion sollte existieren
    if "status" in profile_data:
        if not isinstance(profile_data["status"], dict):
            raise ProfileError(f"Profil '{profile_name}': 'status' muss Dictionary sein.")

    # Snippet-Sektion sollte existieren
    if "snippet" in profile_data:
        if not isinstance(profile_data["snippet"], dict):
            raise ProfileError(f"Profil '{profile_name}': 'snippet' muss Dictionary sein.")


def get_profile(profile_name: str, profiles: Dict[str, Any]) -> Dict[str, Any]:
    """
    Holt ein spezifisches Profil aus der Profil-Liste.

    Args:
        profile_name: Name des gewünschten Profils
        profiles: Dictionary mit allen Profilen

    Returns:
        Profil-Daten

    Raises:
        ProfileError: Wenn Profil nicht existiert
    """
    if profile_name not in profiles:
        available = ", ".join(profiles.keys())
        raise ProfileError(
            f"Profil '{profile_name}' nicht gefunden.\n"
            f"Verfügbare Profile: {available}"
        )

    return profiles[profile_name]


def get_profile_description(profile_name: str, profiles: Dict[str, Any]) -> str:
    """
    Holt die Beschreibung eines Profils (für Tooltips).

    Args:
        profile_name: Name des Profils
        profiles: Dictionary mit allen Profilen

    Returns:
        Beschreibungs-String
    """
    try:
        profile = get_profile(profile_name, profiles)
        return profile.get("description", "Keine Beschreibung verfügbar.")
    except ProfileError:
        return "Profil nicht gefunden."


def get_profile_names(profiles: Dict[str, Any]) -> list[str]:
    """
    Gibt Liste aller Profilnamen zurück.

    Args:
        profiles: Dictionary mit allen Profilen

    Returns:
        Liste der Profilnamen
    """
    return list(profiles.keys())
