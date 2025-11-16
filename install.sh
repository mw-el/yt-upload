#!/usr/bin/env bash
set -euo pipefail

info() { printf "\033[1;34m[INFO]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[WARN]\033[0m %s\n" "$*"; }
error() { printf "\033[1;31m[ERROR]\033[0m %s\n" "$*"; exit 1; }

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="YouTube Upload Tool"
ENV_NAME="yt-upload"
START_SCRIPT="$REPO_DIR/start.sh"
ICON_SOURCE="$REPO_DIR/YT_upl.png"
ICON_TARGET="$HOME/.local/share/icons/yt-upload.png"
DESKTOP_TEMPLATE="$REPO_DIR/yt-upload.desktop"
DESKTOP_TARGET="$HOME/.local/share/applications/yt-upload.desktop"

ensure_conda() {
    if ! command -v conda >/dev/null 2>&1; then
        error "Conda wurde nicht gefunden. Installiere zuerst Miniconda oder Anaconda."
    fi
}

create_env_if_missing() {
    if conda env list | grep -qw "$ENV_NAME"; then
        info "Conda-Environment '$ENV_NAME' ist bereits vorhanden."
        return
    fi

    info "Erstelle Conda-Environment '$ENV_NAME' ..."
    conda create -n "$ENV_NAME" python=3.11 -y
}

install_python_deps() {
    info "Installiere/aktualisiere Python-Abhängigkeiten ..."
    local packages=(
        ttkbootstrap
        pillow
        pydantic
        jsonschema
        python-dotenv
        google-api-python-client
        google-auth
        google-auth-oauthlib
        google-auth-httplib2
        pyyaml
        requests
    )
    conda run -n "$ENV_NAME" pip install --upgrade "${packages[@]}"
}

install_desktop_entry() {
    info "Installiere Desktop-Integration ..."
    mkdir -p "$(dirname "$DESKTOP_TARGET")" "$(dirname "$ICON_TARGET")"
    cp "$ICON_SOURCE" "$ICON_TARGET"

    sed \
        -e "s|__APP_EXEC__|$START_SCRIPT|g" \
        -e "s|__APP_ICON__|$ICON_TARGET|g" \
        "$DESKTOP_TEMPLATE" > "$DESKTOP_TARGET"

    chmod +x "$DESKTOP_TARGET"
    info "Desktop-File erstellt unter $DESKTOP_TARGET"
}

main() {
    info "Starte Installation für $APP_NAME"
    ensure_conda
    create_env_if_missing
    install_python_deps
    install_desktop_entry
    info "Installation abgeschlossen. App kann über '$START_SCRIPT' oder das Desktop-Menü gestartet werden."
}

main "$@"
