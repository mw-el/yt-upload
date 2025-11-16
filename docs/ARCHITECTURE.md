# Architektur-Dokumentation: YouTube Upload Tool

**Version:** 4.0 (Multi-Profil & Automation)
**Letzte Aktualisierung:** 2025-11-13

## Überblick

Das YouTube Upload Tool ist eine Desktop-Anwendung für Ubuntu 24.04, die Videos mit automatisch zugeordneten Metadaten und Untertiteln auf YouTube hochlädt.

**Kernprinzipien:**
- **KISS** (Keep It Simple, Stupid)
- **Separation of Concerns** (Ein Modul = Eine Verantwortlichkeit)
- **Fail Fast** (Sofortiger Abbruch bei Fehlern)

---

## Modulübersicht

### 1. `main.py`
**Verantwortlichkeit:** Einstiegspunkt der Anwendung

- Prüft Conda-Environment (Fail Fast)
- Startet Batch-Upload-GUI
- Minimale Logik, delegiert alles an Module

```python
from app.config import check_environment
from app.gui_batch import run_app
```

---

### 2. `app/config.py`
**Verantwortlichkeit:** Zentrale Konfiguration

**Konstanten:**
- `DEFAULT_PREFIX_LEN = 12` - Präfix-Länge für Datei-Matching
- `DEFAULT_FONT_SIZE = 13` - GUI-Schriftgröße (HiDPI)
- `SUPPORTED_VIDEO_EXTS = [".mp4", ".mov", ".m4v"]`
- OAuth2-Pfade (`CLIENT_SECRETS_PATH`, `TOKEN_PATH`)

**Funktionen:**
- `check_environment()` - Prüft ob im `yt-upload` Conda-Environment

---

### 3. `app/gui_batch.py`
**Verantwortlichkeit:** Batch-Upload-Benutzeroberfläche

**Features:**
- Multi-Video-Auswahl mit Favoriten-Verzeichnissen
- 3-Spalten-Tabelle: Thumbnail | Video+Dateien | Profile
- Inline-Profil-Auswahl (Checkboxen pro Video)
- Manuelle File-Picker für fehlende JSON/SRT (📁-Buttons)
- Reload-Button (↻) pro Video
- Companion-Processing (Container-SRT, Thumbnail-Gen)

**VideoItem-Dataclass:**
```python
@dataclass
class VideoItem:
    video_path: str
    srt_path: Optional[str] = None
    json_path: Optional[str] = None
    softsubs_path: Optional[str] = None  # *_softsubs.mp4
    hardsubs_path: Optional[str] = None  # *_hardsubs.mp4
    thumbnail_path: Optional[str] = None
    companion: Dict[str, bool]  # Status: json, srt_external, srt_container, thumbnail_sample, thumbnail_generated
    selected_profiles: Dict[str, bool]  # Profil-Auswahl
```

---

### 4. `app/matching.py`
**Verantwortlichkeit:** Dateisuche basierend auf Namenskonventionen

**Neue Funktionen (Version 4.0):**

```python
find_specialized_video_files(video_path) -> dict
# Findet: *_softsubs.mp4, *_hardsubs.mp4

find_yt_profile_json(video_path) -> Optional[str]
# Findet: *_yt_profile.json (entfernt Zeitstempel automatisch)

find_sample_thumbnail(video_path) -> Optional[str]
# Findet: sample_*.png (nimmt neuestes)

find_companion_files_multi(video_path) -> Tuple[List[str], List[str]]
# Legacy: Findet SRT/JSON mit Präfix-Matching
```

**Matching-Logik:**
- Entfernt bekannte Suffixe: `_softsubs`, `_hardsubs`, `_podcast`
- Entfernt Zeitstempel: `_20251103_085932`
- Sucht mit Glob-Patterns im Video-Verzeichnis

---

### 5. `app/companion.py`
**Verantwortlichkeit:** ffmpeg-basierte Video-Operationen

**Funktionen:**

```python
check_ffmpeg_available() -> Tuple[bool, str]
# Prüft ob ffmpeg/ffprobe installiert

find_subtitle_streams(video_path) -> Tuple[bool, List[int], str]
# Findet Untertitel-Streams im Container

extract_subtitle_stream(video_path, stream_index) -> Tuple[bool, str, str]
# Extrahiert SRT aus Video-Container

generate_thumbnail(video_path, time_seconds=3) -> Tuple[bool, str, str]
# Generiert Thumbnail aus Video

get_video_companion_files(video_path) -> dict
# Zentrale Funktion: Findet alle Companion-Dateien
# Returns: json_file, softsubs_file, hardsubs_file, srt_file, thumbnail_file
```

**Companion-Processing-Workflow:**
1. Suche `*_yt_profile.json`
2. Suche Video-Varianten (`*_softsubs.mp4`, `*_hardsubs.mp4`)
3. Suche externe SRT (mit Präfix-Matching)
4. Suche `sample_*.png` Thumbnail
5. Falls SRT fehlt → Extraktion aus softsubs-Video
6. Falls Thumbnail fehlt → Generierung bei t=3s

---

### 6. `app/factsheet_schema.py`
**Verantwortlichkeit:** JSON-Schema-Validierung

**Schema (Version 4.0):**
```python
FACTSHEET_SCHEMA = {
    "required": ["snippet", "status"],
    "properties": {
        "source_file": "string",
        "language": "string (de-CH)",
        "snippet": {
            "title": "string (≤100 chars)",
            "description_short": "string",
            "description_bullets": ["string", ...],
            "tags": ["string", ...],
            "hashtags": ["#string", ...],
            "categoryId": "string"
        },
        "status": {
            "privacyStatus": "public|private|unlisted",
            "embeddable": "boolean",
            "madeForKids": "boolean"
        },
        "chapters": [{"timecode": "MM:SS", "title": "string"}],
        "captions": {"file": "string|null", "language": "string"},
        "thumbnail": {"file": "string|null", "autogenerate_if_missing": "boolean"},
        "embed_params": {...},
        "playlist": {...}
    }
}
```

**Wichtig:** Dateiname muss `*_yt_profile.json` sein!

---

### 7. `app/profiles.py`
**Verantwortlichkeit:** Upload-Profil-Verwaltung

**Profil-Format (YAML):**
```yaml
profile_name:
  description: "Tooltip-Text"
  default_selected: true  # Standardmäßig ausgewählt
  requires_srt: false     # Benötigt SRT-Datei
  requires_json: true     # Benötigt JSON-Datei
  status:
    privacyStatus: "unlisted"
    embeddable: true
  snippet:
    categoryId: "22"
  embed_params:
    modestbranding: "1"
    rel: "0"
```

**Standard-Profile:**
- `neutral_embed` - Unlisted, für Website-Embedding
- `public_youtube` - Public, benötigt SRT
- `social_subtitled` - Private, mit eingebrannten Untertiteln

---

### 8. `app/favorites.py`
**Verantwortlichkeit:** Favoriten-Verzeichnisse & Profil-Präferenzen

**Funktionen:**
```python
load_favorites() -> List[dict]
save_favorites(favorites: List[dict])
load_profile_preferences() -> dict  # Speichert letzte Profil-Auswahl pro Video
save_profile_preferences(prefs: dict)
```

**Speicherort:** `~/.config/yt-upload/`
- `favorite_dirs.json` - Favoriten-Verzeichnisse
- `profile_prefs.json` - Profil-Präferenzen pro Video-Basename

---

### 9. `app/uploader.py`
**Verantwortlichkeit:** YouTube-API-Upload

**Vollständig implementiert (Version 2.0+):**
- Video-Upload mit Metadaten
- Untertitel-Upload (SRT)
- Thumbnail-Upload
- Kapitel in Description
- Fehlerbehandlung

```python
upload(
    video_path: str,
    profile: dict,
    factsheet_data: dict,
    srt_path: Optional[str] = None,
    thumbnail_path: Optional[str] = None
) -> UploadResult
```

---

### 10. `app/auth.py`
**Verantwortlichkeit:** OAuth2-Authentifizierung

**Funktionen:**
- `get_authenticated_service()` - Erstellt YouTube-API-Client
- Token-Management (Speicherung, Refresh)
- Browser-basierter OAuth2-Flow

**Token-Speicherort:** `~/.config/yt-upload/token.pickle`

---

### 11. `app/tooltips.py`
**Verantwortlichkeit:** Hover-Tooltips für GUI

**Features:**
- 500ms Verzögerung vor Anzeige
- Automatische Positionierung
- Unterstützt Multiline-Text

---

## Datenfluss

### Video-Hinzufügen
```
1. User wählt Video-Datei(en)
2. get_video_companion_files() sucht alle Companion-Dateien:
   - *_yt_profile.json
   - *_softsubs.mp4 / *_hardsubs.mp4
   - *.srt (externe)
   - sample_*.png
3. JSON-Validierung (factsheet_schema)
4. VideoItem erstellen mit allen Pfaden
5. Companion-Processing starten (async):
   - Falls SRT fehlt → Extraktion aus softsubs-Video
   - Falls Thumbnail fehlt → Generierung bei t=3s
6. GUI-Update mit Status-Anzeige
```

### Upload-Prozess
```
1. User wählt Profile (Checkboxen pro Video)
2. Klick auf "▸ Alle Videos hochladen"
3. Für jedes Video:
   3.1. Für jedes aktivierte Profil:
        - upload() aufrufen mit video, profile, factsheet, srt, thumbnail
        - YouTube-API: Video hochladen
        - YouTube-API: Untertitel hochladen (falls vorhanden)
        - YouTube-API: Thumbnail hochladen (falls vorhanden)
   3.2. Status-Update in GUI: ● Profil: VideoID oder × Profil: Fehler
4. Fertig-Meldung
```

---

## Dateisystem-Struktur

### Typisches Video-Verzeichnis
```
my-video_podcast_20251103_085932_softsubs.mp4   # Video mit Container-SRT
my-video_podcast_20251103_085932_hardsubs.mp4   # Video mit eingebrannten UT
my-video_yt_profile.json                        # YouTube-Metadaten ←
my-video.srt                                    # Externe SRT (optional)
sample_MyVideo_20251102_150059.png              # Thumbnail (bevorzugt)
```

### Konfig-Verzeichnis
```
~/.config/yt-upload/
├── client_secrets.json    # OAuth2-Credentials (von Google Cloud Console)
├── token.pickle           # OAuth2-Token (automatisch generiert)
├── favorite_dirs.json     # Favoriten-Verzeichnisse
└── profile_prefs.json     # Profil-Präferenzen pro Video
```

---

## Design-Entscheidungen

### Warum Präfix-Matching?
- **Problem:** Videos haben oft lange, eindeutige Namen mit Varianten
- **Lösung:** Ersten 12 Zeichen als Präfix nutzen
- **Vorteil:** Flexibel, funktioniert mit verschiedenen Namenskonventionen

### Warum neue Namenskonvention (*_yt_profile.json)?
- **Problem:** Alte JSON-Dateien hatten generische Namen
- **Lösung:** Eindeutige Endung `_yt_profile.json`
- **Vorteil:** Klare Trennung von anderen JSON-Dateien, einfache Suche

### Warum softsubs/hardsubs-Varianten?
- **Problem:** Verschiedene Profile brauchen verschiedene Video-Varianten
- **Lösung:** Separate Dateien mit Suffixen `_softsubs.mp4` / `_hardsubs.mp4`
- **Vorteil:** Ein Upload-Workflow für alle Profile

### Warum sample_*.png bevorzugt?
- **Problem:** Thumbnails aus Video sind oft unscharf oder zeigen falschen Frame
- **Lösung:** Manuell erstellte Thumbnails bevorzugen
- **Vorteil:** Bessere Qualität, zeigt Textanimation nach Abschluss

---

## Fehlerbehandlung (Fail Fast)

### Environment-Check
- Bei Start: Prüfung ob `CONDA_DEFAULT_ENV == "yt-upload"`
- Exit mit klarer Meldung wenn falsch

### JSON-Validierung
- Schema-Validierung vor Upload
- Fehlermeldung mit Pfad zum invaliden Feld

### ffmpeg-Fehler
- Companion-Processing optional (graceful degradation)
- Warnung wenn ffmpeg nicht verfügbar
- App funktioniert auch ohne Container-SRT/Thumbnail-Gen

### Upload-Fehler
- Pro Video+Profil separate Fehlerbehandlung
- Fehler wird angezeigt, andere Uploads laufen weiter
- Status: `× Profil: Fehler` mit Hover-Tooltip für Details

---

## Erweiterbarkeit

### Neue Profile hinzufügen
1. `assets/profiles.yaml` bearbeiten
2. Neues Profil mit `description`, `status`, `snippet` definieren
3. Optional: `requires_srt`, `requires_json` setzen
4. GUI zeigt Profil automatisch an

### Neue Companion-Dateien
1. `app/companion.py`: Neue Funktion in `get_video_companion_files()` hinzufügen
2. `app/gui_batch.py`: VideoItem um neues Feld erweitern
3. `get_companion_status_string()`: Status-Anzeige anpassen

### Neue Datei-Namenskonvention
1. `app/matching.py`: Neue `find_*()` Funktion hinzufügen
2. `app/companion.py`: In `get_video_companion_files()` integrieren

---

**Status:** ✅ Production Ready - Multi-Profil-Upload, Container-SRT-Extraktion, automatische Thumbnails
**Version:** 4.0.0
**Letzte Aktualisierung:** 2025-11-13
