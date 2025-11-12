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

# ====================
# GUI-Konstanten
# ====================
DEFAULT_FONT_FAMILY = "Ubuntu"
DEFAULT_FONT_SIZE = 11
DEFAULT_THEME = "flatly"  # Alternative: "cosmo"

# Fenster-Dimensionen
WINDOW_WIDTH = 700
WINDOW_HEIGHT = 500
WINDOW_MIN_WIDTH = 600
WINDOW_MIN_HEIGHT = 400

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

# Aus .env laden (falls vorhanden)
CLIENT_SECRETS_PATH = os.getenv("YOUTUBE_CLIENT_SECRETS_PATH", DEFAULT_CLIENT_SECRETS_PATH)
TOKEN_PATH = os.getenv("YOUTUBE_TOKEN_PATH", DEFAULT_TOKEN_PATH)
