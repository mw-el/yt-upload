#!/bin/bash
# Automatischer Font-Rendering-Fix für Ubuntu

set -e

echo "================================================"
echo "Font-Rendering-Fix für YouTube Upload Tool"
echo "================================================"
echo ""

# 1. Installiere Tk mit XFT-Support
echo "1. Installiere Tk mit XFT-Support..."
conda install -c conda-forge "tk=8.6.13=xft*" -y

echo ""
echo "2. Setze Environment-Variable..."
conda env config vars set TTKBOOTSTRAP_FONT_MANAGER=tk -n yt-upload

echo ""
echo "================================================"
echo "✓ Font-Fix abgeschlossen!"
echo "================================================"
echo ""
echo "WICHTIG: Aktiviere Environment neu:"
echo "  conda deactivate"
echo "  conda activate yt-upload"
echo ""
echo "Dann App starten:"
echo "  ./start.sh"
echo ""
