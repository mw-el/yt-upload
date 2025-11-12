# YouTube Upload Tool

Minimalistische Desktop-App für automatisierte YouTube-Uploads mit präfix-basiertem Datei-Matching.

**Entwickelt für:** Ubuntu 24.04
**Tech-Stack:** Python 3.11, Tkinter + ttkbootstrap, Google YouTube API v3

---

## Features

- **Automatisches Datei-Matching**: Findet SRT- und JSON-Dateien basierend auf Video-Namenspräfix
- **Profil-basierte Uploads**: Vordefinierte Profile für verschiedene Upload-Szenarien
- **JSON-Schema-Validierung**: Prüft Metadaten vor Upload
- **Moderne GUI**: ttkbootstrap mit Ubuntu-Font
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
│   ├── config.py           # Konfiguration & Environment-Check
│   ├── gui.py              # Benutzeroberfläche (ttkbootstrap)
│   ├── matching.py         # Dateisuche (Präfix-basiert)
│   ├── profiles.py         # Profil-Handling
│   ├── factsheet_schema.py # JSON-Schema-Validierung
│   ├── tooltips.py         # Hover-Tooltips
│   └── uploader.py         # YouTube-Upload (Stub mit TODOs)
├── assets/
│   └── profiles.yaml       # Upload-Profile
├── docs/
│   ├── ARCHITECTURE.md     # Architektur-Dokumentation
│   └── DEVLOG.md           # Entwicklungsfortschritt
├── start.sh                # Starter-Script (aktiviert Environment automatisch)
├── main.py                 # Einstiegspunkt (direkter Start)
├── .env.example            # Environment-Variablen (Vorlage)
└── README.md               # Diese Datei
```

---

## Verwendung

### 1. Video auswählen

Klicke auf **"📹 Video wählen"** und wähle eine Video-Datei (.mp4, .mov, .m4v).

### 2. Automatisches Matching

Die App sucht automatisch nach passenden Dateien im selben Verzeichnis:

**Beispiel:**
```
my_video_123.mp4          ← Video
my_video_123.srt          ← Untertitel (optional)
my_video_123.info.json    ← Metadaten (erforderlich)
└───────────┘
    12 Zeichen Präfix (Standard)
```

**Matching-Logik:**
- Präfix-Länge: 12 Zeichen (konfigurierbar: 10-15)
- Fail Fast bei Mehrfachtreffern

### 3. Metadaten-Format (.info.json)

**Erforderliche Felder:**
```json
{
  "title": "Mein Video-Titel",
  "description": "Detaillierte Beschreibung des Videos"
}
```

**Optionale Felder:**
```json
{
  "tags": ["tag1", "tag2"],
  "category": "22",
  "language": "de",
  "chapters": [
    {"time": "0:00", "title": "Intro"},
    {"time": "1:23", "title": "Hauptteil"}
  ],
  "thumbnail": "/path/to/thumbnail.jpg"
}
```

### 4. Profil wählen

Wähle ein Upload-Profil aus dem Dropdown:

- **neutral_embed**: Unlisted, für Website-Embedding
- **public_youtube**: Öffentlich, maximale Sichtbarkeit
- **social_subtitled**: Privat, für Social-Media-Export

*Fahre mit der Maus über das Dropdown für detaillierte Beschreibungen.*

### 5. Upload starten

Klicke auf **"🚀 Video hochladen"**.

**Status:** Aktuell ist der Upload ein Stub (Simulation). Siehe TODOs in `app/uploader.py` für Implementierung.

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

**Option B: Eigener Pfad mit .env**
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
- Prüfe Pfad: `ls ~/.config/yt-upload/client_secrets.json`
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
# Alle Pakete sind bereits installiert:
# ttkbootstrap, pillow, pydantic, jsonschema,
# python-dotenv, google-api-python-client,
# google-auth, google-auth-oauthlib, pyyaml
```

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

**Ursache:** `.info.json` fehlt Pflichtfelder (`title`, `description`)

**Lösung:** Prüfe JSON-Struktur (siehe Beispiel oben).

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

### Version 3.0 - Erweiterte Features (Geplant)
- [ ] Batch-Upload (mehrere Videos)
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

**Version:** 2.0.0 (Vollständig funktionsfähig)
**Status:** ✅ Production Ready - OAuth2, Video-, Untertitel- und Thumbnail-Upload implementiert
**Getestet auf:** Ubuntu 24.04
**Letzte Aktualisierung:** 2025-11-12
