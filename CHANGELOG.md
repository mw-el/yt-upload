# Changelog: YouTube Upload Tool

Alle wesentlichen Änderungen am Projekt werden hier dokumentiert.

---

## [4.3.0] - 2025-11-22

### ✨ Neue Features

#### Asset-Manager Verbesserungen
- **Video-ID neben Titel:** Zeigt Upload-ID direkt im zugeklappten Akkordeon-Header
  - Gruppierte Videos: Unlisted Video-ID wird angezeigt
  - Einzelne Videos: Video-ID in grauer Schrift neben Titel
- **Löschen-Button im Header:** 🗑-Button direkt im zugeklappten Zustand sichtbar
  - Gruppierte Videos: Löscht alle Varianten nach doppelter Bestätigung
  - Einzelne Videos: Löscht einzelnes Video
- **MD Export:** Neuer Button exportiert Markdown-Tabelle mit Videotiteln und Unlisted-IDs
- **ForKids/Embeddable Checkboxen:** Toggle-Buttons für gruppierte und einzelne Videos
  - Gruppierte Videos: Aktualisiert alle Videos in der Gruppe gleichzeitig

#### SRT-Upload-Logik überarbeitet
- **Profil-basierte SRT-Uploads:** SRT wird nur hochgeladen wenn `requires_srt: true` im Profil
- **Hardsubs-Profil ohne SRT:** `social_subtitled` lädt keine SRT hoch (eingebrannte Untertitel)
- **Softsubs-Extraktion:** SRT wird aus softsubs-Video extrahiert (korrekte Timing inkl. Intro)
- **FFmpeg-basierte Extraktion:** Neue `extract_srt_from_video()` Funktion in uploader.py

### 🐛 Bugfixes

#### SRT-Synchronisation
- **Problem:** Original-SRTs hatten Timing-Offset weil Video-Intro nicht berücksichtigt
- **Lösung:** SRT wird aus softsubs-Video extrahiert (bereits mit korrektem Timing)

### 📚 Dokumentation
- **profiles.yaml aktualisiert:**
  - `neutral_embed`: requires_srt: true (SRT-Upload aktiviert)
  - `public_youtube`: requires_srt: true (SRT-Upload aktiviert)
  - `social_subtitled`: requires_srt: false (keine SRT bei Hardsubs)

---

## [4.2.2] - 2025-11-21

### ✨ Neue Features

#### Asset-Manager: Thumbnail-Upload für gruppierte Videos
- **Multi-Icon Thumbnails:** Gruppierte Videos zeigen Link-Icon (🔗 oben rechts) + Upload-Icon (📤 unten rechts)
- **Koordinaten-basierte Erkennung:** Klick-Position bestimmt Funktion (Link kopieren vs. Thumbnail uploaden)
- **Bulk-Upload:** Thumbnail-Upload für alle Videos in Gruppe gleichzeitig
- **Bestätigungs-Dialog:** Fragt bei mehreren Videos nach Bestätigung

#### GUI-Redesign (schreibszene.ch Branding)
- **Favoriten-Layout:** Alle 4 Buttons (3 Favoriten + 📁) in gemeinsamem Rahmen "Podcast-Bündel-Uploads"
- **Gear-Icon für Favoriten:** ⚙-Button statt separatem Layout
- **Material Design Icons:** Weiß auf Farbe (brightblue #0eb1d2, brightgreen #98ce00, orange #f7b33b)
- **Button-Texte angepasst:**
  - "Quick Upload" → "Einzel Upload"
  - "📚 Assets" → "Videos"
  - YouTube-Buttons: "YT-Kanal", "YT-Studio", "Videos" (ohne Icons)
- **Cleanup:** "YouTube Upload Tool - Batch Mode" Header entfernt, Video-Count-Label entfernt
- **Schwarze Trennlinien:** Im Asset-Manager zwischen Video-Einträgen (2px, #000000)

#### Einzel Upload: Multi-File Improvements
- **Titel-Feld deaktiviert:** Bei mehreren Dateien automatisch deaktiviert
- **Automatische Titel-Generierung:** `-` und `_` werden zu Leerzeichen konvertiert
- **Default-Kategorie:** Education (27) statt People & Blogs (22)
- **Vereinfachte Beschreibung:** Nur Titel, kein "Hochgeladen mit Quick Upload"-Text

### 🐛 Bugfixes

#### Thumbnail-Upload Button (Asset-Manager)
- **Problem:** Upload-Icon bei gruppierten Videos nicht klickbar (nur Link-Funktion aktiv)
- **Lösung:** Neue Methode `_handle_grouped_thumbnail_click()` mit Koordinaten-Erkennung
- **Verhalten:** Link-Icon (oben rechts) kopiert Embed-URL, Upload-Icon (unten rechts) öffnet Dateiauswahl

### 📚 Dokumentation
- **README.md:** Alle Button-Texte und Features aktualisiert
- **README.md:** Asset-Manager Beschreibung mit Icon-Funktionen erweitert
- **README.md:** Version auf 4.2.1 aktualisiert

---

## [4.2.1] - 2025-11-19

### 🐛 Bugfixes

#### Anwendungs-Beendigung
- **Process Cleanup:** Anwendung beendet sich jetzt ordnungsgemäß beim Schließen des Fensters
- **WM_DELETE_WINDOW Handler:** Verhindert, dass Prozesse im Dock verbleiben
- **Sauberes Shutdown:** Ruft `quit()`, `destroy()` und `sys.exit(0)` auf

#### Upload-Status-Meldungen
- **Detaillierte Status-Anzeige:** Verbesserte Status-Meldungen während des Uploads
- **Video-Upload:** "Lade Video hoch: [Dateiname]" → "Video-Upload erfolgreich!"
- **Untertitel-Upload:** "Lade Untertitel hoch: [Dateiname]" → "Untertitel-Upload erfolgreich"
- **Thumbnail-Upload:** "Lade Thumbnail hoch: [Dateiname]" → "Thumbnail-Upload erfolgreich"
- **Klare Fehlermeldungen:** Explizite Fehlermeldungen für jeden Upload-Schritt

---

## [4.2.0] - 2025-11-19

### ✨ Neue Features

#### Quick Upload Dialog

- **Quick Upload Modus:** Separater Dialog für unkomplizierten Upload einzelner Videos
- **Keine JSON-Metadaten erforderlich:** Videos können direkt hochgeladen werden
- **Automatische Titel-Generierung:** Verwendet Dateiname als Standardtitel (überschreibbar)
- **Automatische Thumbnail-Generierung:** Erstes Frame des Videos (t=0s)
- **Flexible Privacy-Einstellungen:** Öffentlich / Nicht gelistet / Privat
- **Kategorien & Sprachen:** 13 YouTube-Kategorien und 6 Sprachen zur Auswahl
- **SRT-Auto-Erkennung:** Sucht automatisch nach passenden Untertitel-Dateien
- **Multi-Video-Upload:** Mehrere Videos auf einmal auswählen und hochladen
- **Fortschrittsanzeige:** Live-Upload-Status und Fehlerbehandlung pro Video

#### Standard-Einstellungen (Quick Upload)

- **Privacy:** "Nicht gelistet" (nicht in Suche, aber einbettbar)
- **Kategorie:** "22 - People & Blogs"
- **Sprache:** "de-CH - Deutsch (Schweiz)"
- **Titel:** Automatisch aus Dateiname
- **Thumbnail:** Erstes Frame (ffmpeg erforderlich)

### 🗂️ Code-Struktur

- **quick_upload_dialog.py:** Neue Modul-Datei für Quick-Upload-Dialog
- **Integration in gui_batch.py:** "Quick Upload…" Button in Favoriten-Toolbar

---

## [4.1.0] - 2025-11-16

### ✨ Neue Features

#### Asset-Manager
- **Asset-Manager-Fenster:** Übersicht über alle hochgeladenen YouTube-Videos
- **Live-Daten:** Abruf via YouTube Data API (Thumbnails, Titel, Views, Privacy)
- **Thumbnail-Upload:** Upload-Icon (orange) unten rechts in Thumbnails
- **Metadaten-Bearbeitung:** Titel, Beschreibung, Tags, Privacy direkt editieren
- **Video-Links:** Direkter Zugriff auf YouTube Studio und Public-URL
- **Statistiken:** Anzeige von Views, Likes, Kommentaren

#### GUI-Modernisierung
- **Neues Theme:** "cosmo" für modernere Optik (statt "flatly")
- **YouTube-Branding:** Offizielle Icons und Farben (#CC0000 weinrot)
- **SVG-Icons:** YouTube-Logo und Upload-Icon aus SVG-Dateien
- **Besseres Layout:** YouTube-Buttons rechts gruppiert (Kanal, Studio, Assets)
- **Trennlinien:** Horizontale Separatoren zwischen Asset-Einträgen

#### Desktop-Integration
- **Desktop-Datei:** `youtube-upload-tool.desktop` für Application Launcher
- **App-Icon:** YouTube Upload Tool erscheint im Menü mit Icon
- **WM-Class:** Korrekte Window-Manager-Integration

### 🗂️ Refactoring
- **svg_icons.py:** Neue zentrale SVG-Icon-Verwaltung
- **Entfernt:** `app/youtube_icon.py` (ersetzt durch svg_icons.py)
- **cairosvg:** Neue Dependency für hochwertige SVG-Konvertierung

### 📚 Dokumentation
- **README.md:** Aktualisierte Projektstruktur und Desktop-Integration
- **CHANGELOG.md:** Vollständige Dokumentation aller Änderungen

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
