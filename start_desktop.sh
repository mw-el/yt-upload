#!/bin/bash
# Desktop startup script for YouTube Upload Tool
# Follows best practices from _AA_DICTATE/docs/DESKTOP_INTEGRATION.md

echo "🚀 Starting YouTube Upload Tool..."

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Find conda installation
if [ -f "$HOME/miniconda3/bin/activate" ]; then
    CONDA_BASE="$HOME/miniconda3"
elif [ -f "$HOME/anaconda3/bin/activate" ]; then
    CONDA_BASE="$HOME/anaconda3"
else
    echo "❌ Error: Cannot find conda installation in $HOME/miniconda3 or $HOME/anaconda3"
    exit 1
fi

# Activate conda base
source "$CONDA_BASE/bin/activate"

# Activate specific environment
conda activate yt-upload

# Verify activation
if [ "$CONDA_DEFAULT_ENV" != "yt-upload" ]; then
    echo "❌ Error: yt-upload environment could not be activated"
    exit 1
fi

echo "✅ Environment yt-upload activated"

# Change to project directory
cd "$SCRIPT_DIR"

# Start the app with explicit conda Python path (critical for desktop integration)
echo "🎯 Starting YouTube Upload Tool..."
"$CONDA_BASE/envs/yt-upload/bin/python" main.py

echo "👋 YouTube Upload Tool closed"
