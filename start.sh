#!/bin/bash
# Starter-Script für YouTube Upload Tool
# Aktiviert automatisch das Conda-Environment und startet die App

set -e  # Bei Fehler abbrechen

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

REQUIRED_ENV="yt-upload"

echo "================================================"
echo "YouTube Upload Tool - Starter"
echo "================================================"
echo ""

# Prüfe, ob Conda verfügbar ist
if ! command -v conda &> /dev/null; then
    echo -e "${RED}❌ FEHLER: Conda ist nicht installiert oder nicht im PATH.${NC}"
    echo "   Installiere Conda oder Miniconda:"
    echo "   https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# Prüfe, ob Environment existiert
if ! conda env list | grep -q "^${REQUIRED_ENV} "; then
    echo -e "${RED}❌ FEHLER: Conda-Environment '${REQUIRED_ENV}' existiert nicht.${NC}"
    echo "   Erstelle es mit:"
    echo "   conda create -n ${REQUIRED_ENV} python=3.11 -y"
    echo "   conda activate ${REQUIRED_ENV}"
    echo "   pip install ttkbootstrap pillow pydantic jsonschema python-dotenv"
    echo "   pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2 pyyaml"
    exit 1
fi

# Prüfe, ob Environment bereits aktiviert ist
if [ "$CONDA_DEFAULT_ENV" = "$REQUIRED_ENV" ]; then
    echo -e "${GREEN}✓ Environment '${REQUIRED_ENV}' ist bereits aktiviert.${NC}"
else
    echo -e "${YELLOW}⚠ Environment '${REQUIRED_ENV}' ist nicht aktiviert.${NC}"
    echo "  Aktiviere Environment..."

    # Finde Conda-Installation
    CONDA_BASE=$(conda info --base)

    # Source conda.sh für conda activate
    source "${CONDA_BASE}/etc/profile.d/conda.sh"

    # Aktiviere Environment
    conda activate "${REQUIRED_ENV}"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Environment '${REQUIRED_ENV}' erfolgreich aktiviert.${NC}"
    else
        echo -e "${RED}❌ FEHLER: Konnte Environment nicht aktivieren.${NC}"
        exit 1
    fi
fi

echo ""
echo "Starte YouTube Upload Tool..."
echo ""

# Setze Font-Rendering-Variable
export TTKBOOTSTRAP_FONT_MANAGER=tk
# Erzwinge Firefox für OAuth (kann via YOUTUBE_OAUTH_BROWSER überschrieben werden)
export YOUTUBE_OAUTH_BROWSER="${YOUTUBE_OAUTH_BROWSER:-firefox}"

# Starte die App
python main.py

# Exit-Code der App weitergeben
exit $?
