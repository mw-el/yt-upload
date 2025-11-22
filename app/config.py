"""
Zentrale Konfigurationskonstanten für YouTube-Upload-App.
Enthält Environment-Prüfung (Fail Fast) und alle Default-Werte.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Lade .env-Datei falls vorhanden
load_dotenv()

# ==================
# Environment-Check
# ==================
DEFAULT_ENV_NAME = "yt-upload"

def check_environment():
    """
    Prüft, ob die App im korrekten Conda-Environment läuft.
    Falls nicht: Klare Fehlermeldung und Exit (Fail Fast).
    """
    current_env = os.environ.get("CONDA_DEFAULT_ENV")
    if current_env != DEFAULT_ENV_NAME:
        print(f"❌ FEHLER: Dieses Tool muss im Conda-Environment '{DEFAULT_ENV_NAME}' laufen.")
        print(f"   Aktuelles Environment: {current_env or 'None'}")
        print(f"\n💡 Empfohlen: Verwende das Starter-Script:")
        print(f"   ./start.sh")
        print(f"\nOder aktiviere das Environment manuell:")
        print(f"   conda activate {DEFAULT_ENV_NAME}")
        print(f"   python main.py")
        sys.exit(1)

# ========================
# Datei-Matching-Konstanten
# ========================
MIN_PREFIX_LEN = 10
MAX_PREFIX_LEN = 15
DEFAULT_PREFIX_LEN = 12

# Unterstützte Dateiformate
SUPPORTED_VIDEO_EXTS = [".mp4", ".mov", ".m4v"]
SUPPORTED_SUB_EXTS = [".srt"]
SUPPORTED_INFO_EXTS = [".json"]
SUPPORTED_THUMB_EXTS = [".png", ".jpg", ".jpeg", ".webp"]

# ====================
# GUI-Konstanten (schreibszene.ch Design)
# ====================
DEFAULT_FONT_FAMILY = "Ubuntu"
DEFAULT_FONT_SIZE = 14  # Basis-Größe wie in _AA_Sprich
DEFAULT_THEME = "cosmo"  # Moderne Themes: "cosmo", "flatly", "litera", "minty"

# schreibszene.ch Farbpalette
COLORS = {
    "szbrightblue":  "#0eb1d2",
    "szgreen":       "#688e26",
    "szbrightgreen": "#98ce00",
    "szorange":      "#f7b33b",
    "szpaper":       "#fffdf9",
    "szred":         "#ff3333",
    "szyellow":      "#fdcb34",
    "szpink":        "#cb20c5",
    "szblue":        "#2176ae",

    "primary":   "#0eb1d2",  # szbrightblue
    "secondary": "#98ce00",  # szbrightgreen
    "tertiary":  "#f7b33b",  # szorange
    "success":   "#688e26",  # szgreen
    "warning":   "#fdcb34",  # szyellow
    "danger":    "#ff3333",  # szred
    "info":      "#2176ae",  # szblue
}

# YouTube-Branding
YOUTUBE_RED = "#CC0000"  # Offizielles YouTube-Rot (weinrot)
YOUTUBE_LOGO = "▶"  # Alternativ: "⏵" oder einfach "YT"

# Fenster-Dimensionen
WINDOW_WIDTH = 900  # Vergrößert für 4 Favoriten-Buttons nebeneinander
WINDOW_HEIGHT = 600
WINDOW_MIN_WIDTH = 800
WINDOW_MIN_HEIGHT = 500

# ====================
# Pfade
# ====================
PROFILES_PATH = "assets/profiles.yaml"

# ====================
# OAuth2-Konfiguration
# ====================
# Standard-Pfade (können über .env überschrieben werden)
DEFAULT_CLIENT_SECRETS_PATH = os.path.expanduser("~/.config/yt-upload/client_secrets.json")
DEFAULT_TOKEN_PATH = os.path.expanduser("~/.config/yt-upload/token.pickle")

# Repo-lokaler Fallback (z.B. ./ .config/client_secrets.json)
REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_CONFIG_DIR = REPO_ROOT / ".config"
LOCAL_CLIENT_SECRETS_PATH = LOCAL_CONFIG_DIR / "client_secrets.json"

# Aus .env laden (falls vorhanden)
CLIENT_SECRETS_PATH = os.getenv("YOUTUBE_CLIENT_SECRETS_PATH")
if not CLIENT_SECRETS_PATH:
    if LOCAL_CLIENT_SECRETS_PATH.exists():
        CLIENT_SECRETS_PATH = str(LOCAL_CLIENT_SECRETS_PATH)
    else:
        CLIENT_SECRETS_PATH = DEFAULT_CLIENT_SECRETS_PATH

TOKEN_PATH = os.getenv("YOUTUBE_TOKEN_PATH", DEFAULT_TOKEN_PATH)

# ====================
# YouTube Channel Links
# ====================
CHANNEL_PUBLIC_URL = os.getenv("YOUTUBE_CHANNEL_URL", "https://www.youtube.com/@SchreibszeneChProfil")
CHANNEL_STUDIO_URL = os.getenv("YOUTUBE_STUDIO_URL", "https://studio.youtube.com/channel/UCHBvwrKQfEwEWt4bKF1p0mQ")
