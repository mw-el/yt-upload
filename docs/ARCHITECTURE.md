# Architektur-Dokumentation: YouTube Upload Tool

## Überblick

Das YouTube Upload Tool ist eine minimalistische Desktop-Anwendung für Ubuntu 24.04, die Videos mit automatisch zugeordneten Metadaten und Untertiteln auf YouTube hochlädt.

**Kernprinzipien:**
- KISS (Keep It Simple, Stupid)
- Separation of Concerns
- Fail Fast

---

## Modulübersicht

### 1. `main.py`
**Verantwortlichkeit:** Einstiegspunkt der Anwendung

- Prüft Conda-Environment (Fail Fast)
- Startet GUI
- Minimale Logik, delegiert alles an Module

### 2. `app/config.py`
**Verantwortlichkeit:** Zentrale Konfiguration

- Konstanten (Pfade, Extensions, GUI-Parameter)
- Environment-Check-Funktion
- Keine Logik, nur Definitionen

### 3. `app/gui.py`
**Verantwortlichkeit:** Benutzeroberfläche

- Verwendet ttkbootstrap (Theme: flatly)
- Ubuntu-Schriftart für optimales Rendering
- Orchestriert alle Module (matching, profiles, factsheet, uploader)
- Event-Handling und State-Management
- Keine Business-Logik

**Widgets:**
- Video-Auswahl-Button
- Automatische Datei-Status-Anzeige (SRT, JSON)
- Profil-Dropdown mit Tooltips
- Upload-Button (aktiviert nur wenn alles validiert)

### 4. `app/matching.py`
**Verantwortlichkeit:** Dateisuche basierend auf Namenspräfix

**Funktionen:**
- `find_companion_files()`: Sucht SRT und JSON im selben Verzeichnis
- Präfix-basiertes Matching (Standard: 12 Zeichen)
- Fail Fast bei Mehrfachtreffern (keine Raterei)
- Validierung der Video-Datei

**Beispiel:**
```
Video:  my_video_123.mp4
SRT:    my_video_123_subtitles.srt
JSON:   my_video_123_info.json
        ^^^^^^^^^^^^
        12 Zeichen Präfix
```

### 5. `app/profiles.py`
**Verantwortlichkeit:** Laden und Validieren von Upload-Profilen

**Funktionen:**
- `load_profiles()`: Lädt YAML-Datei
- `validate_profile()`: Prüft Struktur
- `get_profile_description()`: Holt Beschreibung für Tooltips
- Fail Fast bei ungültigen Profilen

**Profil-Struktur:**
```yaml
profile_name:
  description: "..."
  status:
    privacyStatus: "unlisted"
    embeddable: true
  snippet:
    categoryId: "22"
  embed_params:
    modestbranding: "1"
```

### 6. `app/factsheet_schema.py`
**Verantwortlichkeit:** JSON-Schema-Validierung für Metadaten

**Funktionen:**
- `validate_factsheet()`: Validiert gegen JSON-Schema
- `load_and_validate_factsheet()`: Lädt und validiert in einem Schritt
- Fail Fast bei ungültigen Daten

**Erforderliche Felder:**
- `title` (max. 100 Zeichen)
- `description`

**Optionale Felder:**
- `tags` (max. 500)
- `category`
- `language` (ISO 639-1)
- `chapters` (Array mit `time` und `title`)
- `thumbnail` (Pfad)

### 7. `app/tooltips.py`
**Verantwortlichkeit:** Hover-Tooltips für GUI

**Klasse:** `ToolTip`
- Zeigt Beschreibungen beim Hovern
- Konfigurierbare Verzögerung (Default: 500ms)
- Automatische Positionierung
- Zeilenumbruch bei langen Texten (max. 400px)

### 8. `app/uploader.py`
**Verantwortlichkeit:** YouTube-Upload-Logik (STUB)

**Status:** Stub-Implementierung mit TODOs

**Funktionen:**
- `upload()`: Lädt Video hoch (aktuell: Stub)
- `validate_upload_prerequisites()`: Prüft OAuth2-Credentials (TODO)

**Klasse:** `UploadResult`
- Kapselt Upload-Ergebnis
- Properties: `video_id`, `watch_url`, `embed_url`

**TODOs:**
1. OAuth2-Authentifizierung implementieren
2. Video-Metadaten vorbereiten
3. Video hochladen (google-api-python-client)
4. Untertitel hochladen (falls vorhanden)
5. Thumbnail hochladen (falls vorhanden)

---

## Datenfluss

```
┌──────────┐
│  main.py │ → check_environment()
└────┬─────┘
     │
     ▼
┌─────────────┐
│   gui.py    │ ← run_app()
└──────┬──────┘
       │
       ├─► Video wählen
       │   └─► matching.py: find_companion_files()
       │       ├─► SRT gefunden?
       │       └─► JSON gefunden?
       │           └─► factsheet_schema.py: validate()
       │
       ├─► Profil wählen
       │   └─► profiles.py: load_profiles()
       │       └─► tooltips.py: show description
       │
       └─► Upload-Button
           └─► uploader.py: upload()
               └─► UploadResult
```

---

## Fehlerstrategie

### Fail Fast
Die Anwendung bricht sofort ab bei:

1. **Falschem Environment** (`config.py`)
   - Exit mit klarer Meldung

2. **Fehlenden Profilen** (`profiles.py`)
   - GUI beendet sich mit Fehlerdialog

3. **Mehrfachtreffern beim Matching** (`matching.py`)
   - FileMatchingError mit Liste der gefundenen Dateien

4. **Ungültigen JSON-Metadaten** (`factsheet_schema.py`)
   - Upload-Button bleibt deaktiviert
   - Fehlerdialog mit Details

5. **Upload-Fehlern** (`uploader.py`)
   - UploadError mit klarer Meldung
   - Kein Silent-Fallback

### GUI-Feedback
- Validierungs-Status wird sofort angezeigt
- Upload-Button nur aktiv wenn:
  - Video ausgewählt
  - JSON validiert
  - Profil ausgewählt

---

## Technologie-Entscheidungen

### ttkbootstrap statt tkinter
**Grund:**
- Moderne, professionelle Optik
- Integrierte Themes (flatly, cosmo)
- Bootstrap-ähnliche Komponenten
- Kompatibel mit Standard-Tkinter

**Alternative erwogen:** Qt/PyQt
**Abgelehnt:** Zu heavyweight für MVP

### Ubuntu-Font
**Grund:**
- Optimiert für Ubuntu 24.04 Font-Rendering
- Konsistent mit System-Design
- Gute Lesbarkeit

### YAML für Profile
**Grund:**
- Menschenlesbar und editierbar
- Einfache Struktur für Key-Value-Paare
- Kommentare möglich

**Alternative erwogen:** JSON
**Abgelehnt:** Keine Kommentare, weniger lesbar

### JSON-Schema für Factsheets
**Grund:**
- Standard für JSON-Validierung
- Deklarativ, keine manuelle Prüflogik
- Erweiterbar

---

## Künftige Erweiterungen

### 1. Batch-Upload
- Mehrere Videos gleichzeitig verarbeiten
- Queue-System mit Fortschrittsanzeige

### 2. OAuth2-Credential-Management
- GUI für OAuth2-Setup
- Token-Refresh automatisch

### 3. Erweiterte Profil-Parameter
- Thumbnail-Auswahl
- Playlist-Zuordnung
- Zeitgesteuerte Veröffentlichung

### 4. Preview-Funktion
- Vorschau des Upload-Payloads
- Dry-Run-Modus

### 5. Log-Export
- Detaillierte Upload-Logs
- Fehleranalyse

---

## Dateistruktur

```
/
├── app/
│   ├── __init__.py
│   ├── config.py              # Konfiguration
│   ├── gui.py                 # GUI (ttkbootstrap)
│   ├── matching.py            # Dateisuche
│   ├── profiles.py            # Profil-Handling
│   ├── factsheet_schema.py    # JSON-Validierung
│   ├── tooltips.py            # Tooltip-Logik
│   └── uploader.py            # Upload-Stub
├── assets/
│   └── profiles.yaml          # Upload-Profile
├── docs/
│   ├── ARCHITECTURE.md        # Diese Datei
│   └── DEVLOG.md              # Entwicklungs-Fortschritt
├── main.py                    # Einstiegspunkt
├── .env.example               # OAuth2-Platzhalter
└── README.md                  # Kurzstart-Anleitung
```

---

## Dependencies

Alle Dependencies sind im Conda-Environment `yt-upload` installiert:

- **ttkbootstrap** - Moderne Tkinter-Themes
- **pillow** - Bildverarbeitung (für Thumbnails)
- **pydantic** - Datenvalidierung
- **jsonschema** - JSON-Schema-Validierung
- **python-dotenv** - Environment-Variablen
- **google-api-python-client** - YouTube API
- **google-auth** - Google-Authentifizierung
- **google-auth-oauthlib** - OAuth2-Flow
- **google-auth-httplib2** - HTTP-Adapter
- **pyyaml** - YAML-Parsing

---

**Version:** 1.0.0 (MVP)
**Datum:** 2025-11-12
