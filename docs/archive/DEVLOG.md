# Entwicklungsprotokoll: YouTube Upload Tool

## Projekt-Scope

**Ziel:** Minimalistische Desktop-App für YouTube-Uploads mit automatischer Datei-Zuordnung

**Zielplattform:** Ubuntu 24.04

**Tech-Stack:**
- Python 3.11 (Conda-Environment: yt-upload)
- Tkinter + ttkbootstrap (GUI)
- Google YouTube API v3 (Upload)
- JSON-Schema (Validierung)
- YAML (Konfiguration)

---

## MVP-Features (Version 1.0)

### ✅ Implementiert

1. **Conda-Environment Setup**
   - Environment `yt-upload` erstellt
   - Alle Dependencies installiert

2. **Projektstruktur**
   - Modulare Architektur (Separation of Concerns)
   - Dokumentation (ARCHITECTURE.md, DEVLOG.md)

3. **Environment-Check (Fail Fast)**
   - `config.py`: Prüft Conda-Environment beim Start
   - Exit mit klarer Meldung bei falschem Environment

4. **Datei-Matching**
   - `matching.py`: Präfix-basierte Suche (12 Zeichen)
   - Fail Fast bei Mehrfachtreffern
   - Validierung der Video-Datei

5. **Profil-System**
   - `profiles.py`: Lädt/Validiert YAML-Profile
   - `assets/profiles.yaml`: 3 vordefinierte Profile
     - neutral_embed (unlisted, für Website)
     - public_youtube (öffentlich, SEO)
     - social_subtitled (privat, für Social Media)

6. **JSON-Schema-Validierung**
   - `factsheet_schema.py`: Validiert Metadaten
   - Erforderlich: title, description
   - Optional: tags, category, language, chapters, thumbnail

7. **GUI (ttkbootstrap)**
   - `gui.py`: Hauptfenster mit modernem Design
   - Video-Auswahl mit Datei-Dialog
   - Automatische Anzeige gefundener Dateien
   - Profil-Dropdown mit Hover-Tooltips
   - Upload-Button (nur aktiv wenn alles validiert)

8. **Tooltips**
   - `tooltips.py`: Hover-Erklärungen für Widgets
   - 500ms Verzögerung, automatische Positionierung

9. **Upload-Stub**
   - `uploader.py`: Stub-Implementierung mit TODOs
   - `UploadResult`: Kapselt Ergebnis (video_id, URLs)

---

## Backlog (Post-MVP)

### 🔜 Nächste Schritte

#### Phase 2: YouTube-Upload-Implementierung
- [ ] OAuth2-Authentifizierung implementieren
  - Credentials aus .env oder lokaler Datei laden
  - Token-Refresh-Logik
  - Fehlerbehandlung (ungültige/abgelaufene Token)
- [ ] Video-Upload mit google-api-python-client
  - Metadaten-Mapping (factsheet → YouTube API)
  - Upload mit Fortschrittsanzeige
- [ ] Untertitel-Upload
  - SRT-Datei als Caption hochladen
  - Sprache aus factsheet.language extrahieren
- [ ] Thumbnail-Upload (optional)
  - Falls in factsheet.thumbnail angegeben

#### Phase 3: Erweiterte Features
- [ ] Batch-Upload
  - Mehrere Videos gleichzeitig verarbeiten
  - Queue mit Fortschrittsbalken
- [ ] Kapitel-Upload
  - Kapitel aus factsheet.chapters in Description formatieren
  - Zeitstempel-Format validieren
- [ ] Preview-Funktion
  - Vorschau des Upload-Payloads
  - Dry-Run-Modus (ohne tatsächlichen Upload)

#### Phase 4: Usability
- [ ] Drag & Drop für Video-Dateien
- [ ] Letzte Uploads anzeigen (History)
- [ ] Fehler-Log-Export
- [ ] Einstellungen-Dialog
  - Präfix-Länge konfigurierbar
  - Theme-Auswahl (flatly/cosmo/andere)

#### Phase 5: Testing & Robustheit
- [ ] Unit-Tests für alle Module
- [ ] Integration-Tests für Datei-Matching
- [ ] Mock-Tests für YouTube API
- [ ] Error-Handling-Tests (Netzwerkfehler, API-Quota)

---

## Fortschritt

### 2025-11-12: MVP komplett implementiert ✅

**Implementierte Module:**
- ✅ `main.py` - Einstiegspunkt mit Environment-Check
- ✅ `app/config.py` - Zentrale Konfiguration
- ✅ `app/gui.py` - ttkbootstrap GUI
- ✅ `app/matching.py` - Dateisuche
- ✅ `app/profiles.py` - Profil-Handling
- ✅ `app/factsheet_schema.py` - JSON-Validierung
- ✅ `app/tooltips.py` - Hover-Tooltips
- ✅ `app/uploader.py` - Upload-Stub

**Dokumentation:**
- ✅ `docs/ARCHITECTURE.md` - Architektur-Entscheidungen
- ✅ `docs/DEVLOG.md` - Diese Datei
- ✅ `README.md` - Kurzstart-Anleitung (ausstehend)

**Assets:**
- ✅ `assets/profiles.yaml` - Upload-Profile

**Conda-Environment:**
- ✅ `yt-upload` mit allen Dependencies

**Status:** MVP lauffähig, Upload-Stub bereit für Implementierung

---

## Offene Entscheidungen

### 1. OAuth2-Credential-Management
**Frage:** Wie sollen OAuth2-Credentials gespeichert werden?

**Optionen:**
- A) `.env`-Datei mit Pfad zu `client_secrets.json`
- B) Hardcoded-Pfad in Home-Directory (`~/.config/yt-upload/`)
- C) GUI-Dialog zur Auswahl der Datei

**Vorschlag:** Start mit Option A (flexibel), später Option C für bessere UX

### 2. Upload-Fortschritt
**Frage:** Wie soll Upload-Fortschritt angezeigt werden?

**Optionen:**
- A) Progressbar mit Prozentanzeige
- B) Spinner + "Uploading..."-Text
- C) Console-Output (für MVP)

**Vorschlag:** Option C für MVP, später Option A

### 3. Error-Recovery
**Frage:** Soll Upload bei Netzwerkfehler automatisch wiederholt werden?

**Optionen:**
- A) Kein Retry (Fail Fast)
- B) Automatischer Retry (max. 3x)
- C) Benutzer fragt nach Retry

**Vorschlag:** Option A für MVP (KISS), später Option C

---

## Risiken & Workarounds

### 1. API-Quota-Limits
**Risiko:** YouTube API hat tägliche Quota-Limits (10.000 Units/Tag)

**Mitigation:**
- Upload kostet ~1600 Units
- Monitor Quota-Usage
- Implementiere Quota-Check vor Upload

### 2. OAuth2-Token-Expiration
**Risiko:** Token läuft ab, Upload schlägt fehl

**Mitigation:**
- Token-Refresh automatisch
- Clear Error-Message bei Authentifizierungsfehler
- Anleitung zur Token-Erneuerung in README

### 3. Font-Rendering auf älteren Ubuntu-Versionen
**Risiko:** Ubuntu-Font sieht auf Ubuntu < 24.04 anders aus

**Mitigation:**
- Fallback auf "DejaVu Sans" oder "Liberation Sans"
- Font-Check in config.py (optional)

### 4. Große Video-Dateien
**Risiko:** Upload dauert sehr lange, GUI friert ein

**Mitigation:**
- Chunked-Upload mit Resumable-Upload
- Threading für Upload (GUI bleibt responsive)
- Progress-Callback

---

## Lessons Learned

### Was gut funktioniert hat

1. **Separation of Concerns**
   - Jedes Modul hat klare Verantwortlichkeit
   - Einfaches Testing möglich

2. **Fail Fast**
   - Klare Fehlermeldungen von Anfang an
   - Keine unklaren Zustände

3. **ttkbootstrap**
   - Sehr einfach zu verwenden
   - Professionelles Aussehen out-of-the-box

4. **JSON-Schema**
   - Deklarative Validierung
   - Keine manuelle if/else-Logik

### Was verbessert werden kann

1. **Type-Hints**
   - Noch konsequenter verwenden (z.B. in gui.py)
   - mypy für statische Typ-Prüfung

2. **Error-Handling**
   - Mehr spezifische Exception-Klassen
   - Context-Manager für File-Handling

3. **Testing**
   - Unit-Tests von Anfang an schreiben
   - Test-Fixtures für Mock-Daten

---

## Nächste Schritte (Priorität)

1. **README.md schreiben** (🔴 Hoch)
   - Kurzstart-Anleitung
   - Environment-Setup
   - Beispiel-Usage

2. **OAuth2 implementieren** (🔴 Hoch)
   - Ohne Upload keine funktionierende App

3. **Video-Upload implementieren** (🔴 Hoch)
   - Core-Feature

4. **Testing schreiben** (🟡 Mittel)
   - Zumindest für kritische Module (matching, profiles)

5. **Batch-Upload** (🟢 Niedrig)
   - Nice-to-have, nicht kritisch

---

**Letzte Aktualisierung:** 2025-11-12
**Version:** 1.0.0 (MVP)
**Status:** ✅ Bereit für OAuth2-Implementierung
