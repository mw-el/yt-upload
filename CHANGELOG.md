# Changelog: YouTube Upload Tool

Alle wesentlichen Änderungen am Projekt werden hier dokumentiert.

---

## [4.0.0] - 2025-11-13

### ✨ Neue Features

#### Namenskonventionen & Datei-Matching
- **Neue JSON-Namenskonvention:** `*_yt_profile.json` für YouTube-Metadaten
- **Video-Varianten:** Unterstützung für `*_softsubs.mp4` und `*_hardsubs.mp4`
- **Sample-Thumbnails:** Automatische Erkennung von `sample_*.png` Dateien
- **Intelligentes Matching:** Entfernt Zeitstempel und Suffixe automatisch

#### GUI-Verbesserungen
- **Manuelle File-Picker:** 📁-Buttons für fehlende JSON/SRT-Dateien
- **Erweiterte Status-Anzeige:** Zeigt Quelle der Dateien (ext/cont/sample/gen)
- **Video-Varianten-Anzeige:** Status zeigt softsubs/hardsubs-Verfügbarkeit
- **Favoriten mit Verzeichnisnamen:** Buttons zeigen tatsächlichen Ordnernamen
- **Größere Schriften:** Font-Size auf 13 für HiDPI-Bildschirme erhöht
- **Breiteres Fenster:** 900x600 Pixel für bessere Übersicht

#### Backend-Verbesserungen
- **Neue Companion-Logik:** Zentrale `get_video_companion_files()` Funktion
- **Softsubs-Präferenz:** SRT-Extraktion bevorzugt softsubs-Video
- **Thumbnail-Präferenz:** Sample-PNG bevorzugt vor generiertem Thumbnail
- **JSON-Schema aktualisiert:** Validierung für neue Struktur (snippet, status, etc.)

### 📚 Dokumentation
- **PROMPT_YT_METADATA.md:** Vollständige LLM-Prompt-Vorlage hinzugefügt
- **ARCHITECTURE.md:** Komplett überarbeitet für Version 4.0
- **README.md:** Aktualisiert mit neuen Features und Workflows

### 🗂️ Refactoring
- **Legacy-Code archiviert:** `app/gui.py` (single-video GUI) verschoben
- **Beispiel-JSONs aktualisiert:** Alte Beispiele archiviert
- **Code-Cleanup:** Veraltete Funktionen entfernt

---

## [3.0.0] - 2025-XX-XX (Vorherige Version)

### ✨ Neue Features
- **Batch-Upload:** Mehrere Videos gleichzeitig hochladen
- **Video-Liste:** Treeview mit Status-Tracking
- **Sequentieller Upload:** Vermeidet API-Limits
- **Fortschrittsanzeige:** Live-Status pro Video

---

## [2.0.0] - 2025-XX-XX

### ✨ Neue Features
- **OAuth2-Authentifizierung:** Vollständig implementiert
- **Video-Upload:** YouTube-API-Integration
- **Untertitel-Upload:** SRT-Dateien hochladen
- **Thumbnail-Upload:** Custom Thumbnails
- **Kapitel-Upload:** In Description formatiert
- **Automatisches Token-Refresh:** OAuth2-Token-Verwaltung

---

## [1.0.0] - 2025-XX-XX (MVP)

### ✨ Neue Features
- **Conda-Environment Setup:** `yt-upload` Environment
- **GUI mit ttkbootstrap:** Moderne Benutzeroberfläche
- **Datei-Matching:** Präfix-basierte Suche
- **Profil-System:** YAML-basierte Upload-Profile
- **JSON-Validierung:** Schema-basierte Metadaten-Validierung
- **Fail Fast:** Klare Fehlermeldungen bei Problemen

---

## Legende

- ✨ Neue Features
- 🐛 Bugfixes
- 📚 Dokumentation
- 🗂️ Refactoring
- ⚠️ Breaking Changes
- 🔒 Security

---

**Hinweis:** Frühere Versionen (1.0-3.0) wurden nicht vollständig dokumentiert.
