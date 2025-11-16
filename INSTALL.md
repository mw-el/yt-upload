# Installation – YouTube Upload Tool

Diese Anleitung beschreibt, wie du das Tool auf einem neuen Ubuntu‑System installierst und direkt als Desktop-App nutzen kannst.

## Voraussetzungen

- Ubuntu 24.04 (oder kompatibel)
- Git
- Conda (Miniconda oder Anaconda)

## Schritte

1. **Repository klonen**
   ```bash
   git clone https://github.com/<DEIN-ACCOUNT>/yt-upload-tool.git
   cd yt-upload-tool
   ```

2. **Installations-Skript ausführen**
   ```bash
   chmod +x install.sh
   ./install.sh
   ```
   Das Skript erledigt alles Weitere:
   - erstellt (falls nötig) das Conda-Environment `yt-upload`
   - installiert/aktualisiert alle Python-Abhängigkeiten
   - kopiert das App-Icon nach `~/.local/share/icons/`
   - installiert unter `~/.local/share/applications/` einen Desktop-Launcher

3. **App starten**
   - Über das Anwendungsmenü (Suche nach „YouTube Upload Tool“)
   - oder direkt im Repo:
     ```bash
     ./start.sh
     ```

## Deinstallation / Aktualisierung

- Desktop-Integration entfernen:
  ```bash
  rm ~/.local/share/applications/yt-upload.desktop
  rm ~/.local/share/icons/yt-upload.png
  ```
- Conda-Environment löschen:
  ```bash
  conda env remove -n yt-upload
  ```
- Repository-Verzeichnis löschen oder über `git pull` aktualisieren.
