# YouTube Upload Tool

Minimalistische Desktop-App für automatisierte YouTube-Uploads mit präfix-basiertem Datei-Matching.

**Entwickelt für:** Ubuntu 24.04
**Tech-Stack:** Python 3.11, Tkinter + ttkbootstrap, Google YouTube API v3

---

## Features

- **Multi-Profil-Batch-Upload**: Mehrere Videos mit verschiedenen Profilen gleichzeitig hochladen
- **Favoriten-Verzeichnisse**: Schnellzugriff auf häufig genutzte Ordner
- **Automatisches Datei-Matching**: Findet SRT- und JSON-Dateien basierend auf Video-Namenspräfix
- **Container-SRT-Extraktion**: Extrahiert Untertitel automatisch aus Video-Container (ffmpeg)
- **Automatische Thumbnail-Generierung**: Erstellt Thumbnail bei t=3s (ffmpeg)
- **Profil-basierte Uploads**: Vordefinierte Profile mit Requirements (SRT, JSON)
- **Profil-Präferenzen**: Speichert letzte Profil-Auswahl pro Video
- **JSON-Schema-Validierung**: Prüft Metadaten vor Upload
- **Moderne GUI**: ttkbootstrap mit Ubuntu-Font, responsives Layout
- **Fail Fast**: Klare Fehlermeldungen bei Problemen

---

## Schnellstart

⚠️ **Wichtig:** Falls Schriften pixelig aussehen, siehe **[FONT_FIX.md](FONT_FIX.md)** für einen 2-Befehl-Fix!

### 1. Voraussetzungen

- Ubuntu 24.04
- Conda installiert
- Git (optional)

### 2. App starten (Empfohlen)

**Mit Starter-Script (aktiviert Environment automatisch):**

```bash
./start.sh
```

Das Script:
- Prüft, ob Conda verfügbar ist
- Prüft, ob Environment `yt-upload` existiert
- Aktiviert das Environment automatisch
- Startet die App

### 3. Alternative: Manuelle Aktivierung

Falls du das Environment lieber manuell aktivieren möchtest:

```bash
conda activate yt-upload
python main.py
```

**Wichtig:** Die App läuft nur im `yt-upload`-Environment. Bei falschem Environment erscheint eine klare Fehlermeldung mit Hinweis auf `./start.sh`.

---

## Projektstruktur

```
/
├── app/                    # Haupt-Anwendungslogik
│   ├── auth.py             # OAuth2-Authentifizierung
│   ├── companion.py        # Container-SRT & Thumbnail (ffmpeg)
│   ├── config.py           # Konfiguration & Environment-Check
│   ├── favorites.py        # Favoriten-Verzeichnisse & Profil-Präferenzen
│   ├── gui.py              # Einzelvideo-GUI (Legacy)
│   ├── gui_batch.py        # Multi-Profil-Batch-GUI (Standard)
│   ├── matching.py         # Dateisuche (Präfix-basiert)
│   ├── profiles.py         # Profil-Handling
│   ├── factsheet_schema.py # JSON-Schema-Validierung
│   ├── tooltips.py         # Hover-Tooltips
│   └── uploader.py         # YouTube-Upload (vollständig implementiert)
├── assets/
│   └── profiles.yaml       # Upload-Profile (mit default_selected, requires_*)
├── docs/
│   ├── ARCHITECTURE.md     # Architektur-Dokumentation
│   ├── DEVLOG.md           # Entwicklungsfortschritt
│   └── README_OAUTH.md     # OAuth2-Setup-Anleitung
├── start.sh                # Starter-Script (aktiviert Environment automatisch)
├── fix_fonts.sh            # Font-Fix für Ubuntu
├── main.py                 # Einstiegspunkt (startet Batch-Upload-GUI)
├── .env.example            # Environment-Variablen (Vorlage)
└── README.md               # Diese Datei
```

---

## Verwendung

### 1. Videos auswählen

**Option A: Favoriten-Buttons**
Klicke auf einen Favoriten-Button (zeigt Verzeichnisnamen wie "Podcasts", "Videos", etc.) → öffnet Datei-Dialog im entsprechenden Verzeichnis.

**Option B: Manuell**
Klicke auf **"+ Videos hinzufügen"** und navigiere zum Verzeichnis.

**Tipp:** Halte `Strg` gedrückt für Multi-Select oder `Shift` für Bereichsauswahl.

**Favoriten konfigurieren:** Klicke auf ● neben Favorit → wähle neues Verzeichnis. Der Button zeigt automatisch den Namen des ausgewählten Verzeichnisses.

### 2. Automatisches Matching

Die App sucht automatisch nach passenden Dateien im selben Verzeichnis für **jedes** ausgewählte Video:

**Beispiel (neue Namenskonventionen):**
```
my-video_podcast_20251103_085932_softsubs.mp4   ← Video mit Container-SRT
my-video_podcast_20251103_085932_hardsubs.mp4   ← Video mit eingebrannten Untertiteln
my-video_yt_profile.json                        ← YouTube-Metadaten (WICHTIG!)
my-video.srt                                    ← Externe SRT (optional)
sample_MyVideo_20251102_150059.png              ← Thumbnail (bevorzugt)
```

**Matching-Logik:**
- Sucht `*_yt_profile.json` für Metadaten
- Sucht `*_softsubs.mp4` / `*_hardsubs.mp4` für Video-Varianten
- Sucht `*.srt` für externe Untertitel (mit Präfix-Matching)
- Sucht `sample_*.png` für Thumbnails
- Bei fehlender SRT: Automatische Extraktion aus softsubs-Video
- Bei fehlendem Thumbnail: Generierung aus Video bei t=3s

### 3. Metadaten-Format (*_yt_profile.json)

**Wichtig:** Dateiname MUSS `*_yt_profile.json` sein!

**Erforderliche Felder:**
```json
{
  "snippet": {
    "title": "Mein Video-Titel (≤80 Zeichen)"
  },
  "status": {
    "privacyStatus": "unlisted"
  }
}
```

**Vollständiges Beispiel:**
```json
{
  "source_file": "my-video",
  "language": "de-CH",
  "snippet": {
    "title": "Mein Video-Titel",
    "description_short": "Kurze Beschreibung in 2 Sätzen.",
    "description_bullets": [
      "Punkt 1",
      "Punkt 2"
    ],
    "tags": ["tag1", "tag2"],
    "hashtags": ["#Tag1", "#Tag2"],
    "categoryId": "22"
  },
  "status": {
    "privacyStatus": "unlisted",
    "embeddable": true,
    "madeForKids": false
  },
  "chapters": [
    {"timecode": "00:00", "title": "Intro"},
    {"timecode": "01:23", "title": "Hauptteil"}
  ],
  "captions": {
    "file": "./my-video.srt",
    "language": "de-CH"
  },
  "thumbnail": {
    "file": null,
    "autogenerate_if_missing": true,
    "autogenerate_frame_sec": 3
  }
}
```

**Siehe auch:** `docs/PROMPT_YT_METADATA.md` für LLM-Prompt zur Generierung

### 4. Profile wählen

**Pro Video einzeln:**
1. Wähle Video in Liste aus
2. Rechtes Panel zeigt verfügbare Profile mit Checkboxen
3. Aktiviere gewünschte Profile (mehrere möglich!)

**Verfügbare Profile:**
- **neutral_embed** (Standard): Unlisted, für Website-Embedding
- **public_youtube**: Öffentlich, benötigt SRT
- **social_subtitled**: Privat, benötigt SRT

Profile mit fehlenden Requirements werden automatisch deaktiviert (z.B. "public_youtube (fehlt: SRT)").

**Präferenzen:** Profil-Auswahl wird pro Video-Basename gespeichert und beim nächsten Mal wiederhergestellt.

### 5. Batch-Upload starten

Klicke auf **"▸ Alle hochladen"**.

**Upload-Prozess:**
- Jedes Video wird für **jedes aktivierte Profil** hochgeladen
- Sequentielle Verarbeitung (vermeidet API-Limits)
- Live-Status-Updates pro Video+Profil

**Status-Symbole:**
- **↻ Profil: Läuft...**: Upload läuft gerade
- **● Profil: VideoID**: Upload erfolgreich
- **× Profil: Fehler**: Upload fehlgeschlagen
- **○ Profil: JSON/SRT fehlt**: Requirements nicht erfüllt

**Beispiel:**
```
my_video.mp4
↻ neutral_embed: Läuft...
● public_youtube: abc12345...
```

---

## Profile anpassen

Profile sind in `assets/profiles.yaml` definiert:

```yaml
mein_profil:
  description: |
    Beschreibung für Tooltip.
    Mehrere Zeilen möglich.
  status:
    privacyStatus: "unlisted"  # public, private, unlisted
    embeddable: true
  snippet:
    categoryId: "22"  # YouTube-Kategorie
  embed_params:
    modestbranding: "1"
    rel: "0"
```

**Kategorie-IDs:**
- 22: People & Blogs
- 27: Education
- 28: Science & Technology
- [Vollständige Liste](https://developers.google.com/youtube/v3/docs/videoCategories/list)

---

## OAuth2-Setup (ERFORDERLICH)


### Schritt 1: Google Cloud Console einrichten

1. **Gehe zu Google Cloud Console:**
   - Öffne [console.cloud.google.com](https://console.cloud.google.com)
   - Logge dich mit deinem Google-Konto ein

2. **Erstelle ein Projekt:**
   - Klicke oben auf "Projekt auswählen"
   - "Neues Projekt"
   - Name: z.B. "YouTube Upload Tool"
   - Klicke "Erstellen"

3. **Aktiviere YouTube Data API v3:**
   - Gehe zu "APIs & Services" > "Bibliothek"
   - Suche nach "YouTube Data API v3"
   - Klicke auf "Aktivieren"

4. **Erstelle OAuth2-Credentials:**
   - Gehe zu "APIs & Services" > "Credentials"
   - Klicke "+ CREDENTIALS ERSTELLEN"
   - Wähle "OAuth-Client-ID"
   - Falls "Zustimmungsbildschirm konfigurieren" erscheint:
     - Wähle "Extern"
     - App-Name: "YouTube Upload Tool"
     - Nutzer-Support-E-Mail: deine E-Mail
     - Entwickler-E-Mail: deine E-Mail
     - Speichern
   - Anwendungstyp: "Desktop-App"
   - Name: "YouTube Upload Tool Client"
   - Klicke "Erstellen"

5. **Credentials herunterladen:**
   - Klicke auf "JSON HERUNTERLADEN"
   - Speichere die Datei als `client_secrets.json`

### Schritt 2: Credentials platzieren

**Option A: Standard-Pfad (empfohlen)**
```bash
mkdir -p ~/.config/yt-upload
mv ~/Downloads/client_secrets.json ~/.config/yt-upload/
```

**Option B: Repo-lokaler Pfad (wird automatisch erkannt)**
```bash
mkdir -p .config
mv ~/Downloads/client_secrets.json .config/client_secrets.json
```

**Option C: Eigener Pfad mit .env**
```bash
cp .env.example .env
# Bearbeite .env:
echo "YOUTUBE_CLIENT_SECRETS_PATH=/pfad/zu/deiner/client_secrets.json" >> .env
```

### Schritt 3: Erste Authentifizierung

1. Starte die App:
   ```bash
   ./start.sh
   ```

2. Wähle ein Video und starte Upload

3. **Browser öffnet sich automatisch:**
   - Wähle dein Google-Konto
   - Klicke "Zulassen"
   - Du siehst: "Authentifizierung erfolgreich!"
   - Browser-Fenster kann geschlossen werden

4. **Token wird gespeichert:**
   - Token wird in `~/.config/yt-upload/token.pickle` gespeichert
   - Bei zukünftigen Uploads kein Browser-Login mehr nötig
   - Token wird automatisch erneuert wenn abgelaufen

### Troubleshooting OAuth2

**"OAuth2-Credentials nicht gefunden"**
- Prüfe Pfade: `ls ~/.config/yt-upload/client_secrets.json` **oder** `ls .config/client_secrets.json`
- Stelle sicher, dass Datei heißt: `client_secrets.json` (nicht `client_secret_...json`)

**"Token-Refresh fehlgeschlagen"**
- Lösche alten Token: `rm ~/.config/yt-upload/token.pickle`
- Starte Upload erneut → Browser-Login erscheint wieder

**"Access blocked: Authorization Error"**
- App ist noch im Testing-Modus in Google Cloud Console
- Lösung 1: Füge deine E-Mail als Test-User hinzu (Cloud Console > OAuth consent screen > Test users)
- Lösung 2: Publish app (nur nötig für andere Benutzer)

---

## Entwicklung

### Module installieren

Alle Dependencies sind bereits im `yt-upload`-Environment:

```bash
conda activate yt-upload
# Python-Pakete:
# ttkbootstrap, pillow, pydantic, jsonschema,
# python-dotenv, google-api-python-client,
# google-auth, google-auth-oauthlib, pyyaml
```

**Zusätzlich erforderlich (System):**
```bash
sudo apt install ffmpeg ffprobe
# Für Container-SRT-Extraktion und Thumbnail-Generierung
```

**Hinweis:** Ohne ffmpeg funktioniert die App, aber Container-SRT und Thumbnails werden nicht automatisch verarbeitet.

### Konfiguration anpassen

Siehe `app/config.py`:

```python
MIN_PREFIX_LEN = 10          # Minimale Präfix-Länge
MAX_PREFIX_LEN = 15          # Maximale Präfix-Länge
DEFAULT_PREFIX_LEN = 12      # Standard-Präfix-Länge
DEFAULT_THEME = "flatly"     # GUI-Theme
```

### Tests schreiben

Für künftige Tests:
```bash
conda activate yt-upload
pip install pytest
pytest tests/
```

---

## Fehlerbehebung

### "Dieses Tool muss im Conda-Environment 'yt-upload' laufen"

**Lösung:**
```bash
conda activate yt-upload
python main.py
```

### "Profil-Datei nicht gefunden"

**Lösung:** Stelle sicher, dass `assets/profiles.yaml` existiert und im Projektverzeichnis läuft.

### "JSON-Validierung fehlgeschlagen"

**Ursache:** `*_yt_profile.json` fehlt Pflichtfelder (`snippet`, `status`) oder hat falsches Format

**Lösung:**
- Prüfe dass Dateiname `*_yt_profile.json` ist
- Verwende korrektes Format (siehe Abschnitt "Metadaten-Format")
- Siehe `docs/PROMPT_YT_METADATA.md` für LLM-Prompt zur Generierung

### "Mehrdeutiger Match für Präfix"

**Ursache:** Mehrere Dateien mit gleichem Präfix gefunden

**Lösung:** Benenne Dateien um, sodass Präfix eindeutig ist.

---

## Architektur

**Prinzipien:**
- **KISS** (Keep It Simple, Stupid)
- **Separation of Concerns** (Ein Modul = Eine Verantwortlichkeit)
- **Fail Fast** (Sofortiger Abbruch bei Fehlern)

**Details:** Siehe `docs/ARCHITECTURE.md`

---

## Roadmap

### Version 1.0 - MVP ✅
- [x] Conda-Environment Setup
- [x] GUI mit ttkbootstrap
- [x] Datei-Matching
- [x] Profil-System
- [x] JSON-Validierung

### Version 2.0 - Vollständiger Upload ✅ (AKTUELL)
- [x] OAuth2-Authentifizierung
- [x] Video-Upload implementiert
- [x] Untertitel-Upload implementiert
- [x] Thumbnail-Upload implementiert
- [x] Upload-Fortschrittsanzeige
- [x] Automatisches Token-Refresh
- [x] Kapitel-Upload (in Description)

### Version 3.0 - Batch Upload ✅
- [x] Batch-Upload (mehrere Videos)
- [x] Video-Liste mit Status-Tracking
- [x] Sequentieller Upload aller Videos
- [x] Fortschrittsanzeige pro Video

### Version 4.0 - Multi-Profil & Automation ✅ (AKTUELL)
- [x] Multi-Profil-Upload (ein Video → mehrere Profile)
- [x] Favoriten-Verzeichnisse mit Schnellzugriff
- [x] Container-SRT-Extraktion (ffmpeg)
- [x] Automatische Thumbnail-Generierung (t=3s)
- [x] Profil-Requirements (requires_srt, requires_json)
- [x] Profil-Präferenzen-Speicherung
- [x] Companion-Status-Anzeige (● ◐ ○)

### Version 5.0 - Erweiterte Features (Geplant)
- [ ] Playlist-Zuordnung
- [ ] Preview-Funktion (Dry-Run)
- [ ] Drag & Drop
- [ ] Video-Scheduling (zeitgesteuerte Veröffentlichung)
- [ ] Upload-History mit Log-Export

**Details:** Siehe `docs/DEVLOG.md`

---

## Lizenz

Proprietär (noch nicht definiert)

---

## Support

Bei Fragen oder Problemen:
- Siehe Dokumentation in `docs/`
- OAuth2-Setup: Siehe Abschnitt "OAuth2-Setup (ERFORDERLICH)" oben
- Troubleshooting: Siehe Abschnitt "Fehlerbehebung"

---

**Version:** 4.0.0 (Multi-Profil & Automation)
**Status:** ✅ Production Ready - Multi-Profil-Upload, Container-SRT-Extraktion, automatische Thumbnails
**Abhängigkeiten:** Python 3.11, ffmpeg/ffprobe (optional für SRT/Thumbnail)
**Getestet auf:** Ubuntu 24.04
**Letzte Aktualisierung:** 2025-11-13
