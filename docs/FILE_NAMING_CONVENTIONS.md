# Datei-Namenskonventionen: YouTube Upload Tool

**Version:** 4.3.0
**Letzte Aktualisierung:** 2025-11-22
**Status:** ✅ Stabil - SRT-Extraktion aus Softsubs-Video

---

## Übersicht

Das YouTube Upload Tool erwartet spezifische Datei-Namenskonventionen, um Companion-Dateien (SRT, JSON, Thumbnails, Video-Varianten) automatisch zu finden.

**Wichtig:** Diese Dokumentation beschreibt die **aktuellen Erwartungen** der App. Abweichungen führen dazu, dass Dateien nicht automatisch erkannt werden.

---

## Basis-Namensextraktion

Die App extrahiert den "Basis-Namen" aus Video-Dateinamen durch Entfernen von:

1. **Bekannte Suffixe** (iterativ, in beliebiger Reihenfolge):
   - `_softsubs`
   - `_hardsubs`
   - `_podcast`

2. **Zeitstempel-Pattern** (Format: `_YYYYMMDD_HHMMSS`):
   - Beispiel: `_20251111_205254`

**Algorithmus:**
```
Input:  die-sonnenseite-der-klischees_podcast_20251111_205254_softsubs
Step 1: Entferne _softsubs → die-sonnenseite-der-klischees_podcast_20251111_205254
Step 2: Entferne _20251111_205254 → die-sonnenseite-der-klischees_podcast
Step 3: Entferne _podcast → die-sonnenseite-der-klischees
Output: die-sonnenseite-der-klischees
```

**Code:** `app/matching.py::_extract_base_name()`

---

## Video-Dateien

### Primäre Video-Datei
**Format:** Beliebiger Name mit `.mp4`, `.mov`, oder `.m4v`

**Beispiele:**
```
video.mp4
my-video_podcast_20251111_205254_softsubs.mp4
simple-name.mov
```

### Video-Varianten

#### Softsubs-Video (bevorzugt für SRT-Extraktion)
**Pattern:** `{basis}_podcast_{zeitstempel}_softsubs.mp4`
**Beschreibung:** Video mit Container-Untertiteln (SRT im MKV/MP4-Container eingebettet)

**Beispiel:**
```
die-sonnenseite-der-klischees_podcast_20251111_205254_softsubs.mp4
```

**Erkennung:**
- Glob-Pattern: `{basis}*_softsubs.mp4`
- Bevorzugt für SRT-Extraktion wenn keine externe SRT vorhanden

#### Hardsubs-Video
**Pattern:** `{basis}_podcast_{zeitstempel}_hardsubs.mp4`
**Beschreibung:** Video mit eingebrannten Untertiteln (burned-in subtitles)

**Beispiel:**
```
die-sonnenseite-der-klischees_podcast_20251111_205254_hardsubs.mp4
```

**Erkennung:**
- Glob-Pattern: `{basis}*_hardsubs.mp4`
- Verwendet für `social_subtitled` Profil (keine separate SRT benötigt)

---

## Untertitel-Dateien (SRT)

### Externe SRT-Datei
**Pattern 1 (Präfix-Matching):** `{präfix}*.srt` (erste 12 Zeichen des Video-Namens)
**Pattern 2 (Basis-Name):** `{basis}.srt`

**Beispiele:**
```
die-sonnenseite-der-klischees.srt                    ✓ (Basis-Name)
die-sonnenseite-der-klischees_podcast_20251111_205254_softsubs.srt  ✓ (Vollständiger Name)
die sonnenseite des klischees.srt                    ✓ (mit Leerzeichen)
```

**Priorität:**

1. Externe SRT-Datei (wenn gefunden)
2. Container-SRT aus softsubs-Video (automatisch extrahiert)

**Wichtig (Version 4.3):** SRT wird aus dem softsubs-Video extrahiert, weil dort das Timing bereits korrekt ist (inkl. Intro). Original-SRTs haben oft einen Timing-Offset.

**SRT-Upload-Logik:**

- `neutral_embed`: SRT wird hochgeladen (requires_srt: true)
- `public_youtube`: SRT wird hochgeladen (requires_srt: true)
- `social_subtitled`: Keine SRT (requires_srt: false, Hardsubs haben eingebrannte UT)

**Hinweis:** Leerzeichen in Dateinamen sind erlaubt!

---

## JSON-Metadaten

### YouTube-Profil-JSON
**Pattern:** `{basis}*_yt_profile.json`
**WICHTIG:** Muss `_yt_profile.json` am Ende haben!

**Beispiele:**
```
die-sonnenseite-der-klischees_yt_profile.json        ✓ (korrekt)
my-video_yt_profile.json                             ✓ (korrekt)
Untitled_template_20251111_210806.json               ✗ (falsch - fehlt _yt_profile)
video.info.json                                      ✗ (falsch - altes Format)
```

**Schema:** Siehe `docs/PROMPT_YT_METADATA.md`

**Required Fields:**
- `snippet.title`
- `status.privacyStatus`

---

## Thumbnail-Dateien

### ⚠️ AKTUELLE LIMITATIONS

Die App sucht nach folgenden Patterns (in dieser Reihenfolge):

#### Pattern 1: Basis-Name + _thumbnail.png
**Pattern:** `{basis}*_thumbnail.png`
**Status:** 🔧 Implementiert, aber **nicht getestet**

**Erwartete Beispiele:**
```
die-sonnenseite-der-klischees_thumbnail.png          ✓ (sollte funktionieren)
die-sonnenseite-der-klischees_20251111_205254_thumbnail.png  ✓ (sollte funktionieren)
```

#### Pattern 2: sample_*.png (Fallback)
**Pattern:** `sample_*.png`
**Status:** 🔧 Implementiert, nimmt neueste Datei

**Erwartete Beispiele:**
```
sample_MyVideo_20251102_150059.png                   ✓ (sollte funktionieren)
sample_thumbnail.png                                 ✓ (sollte funktionieren)
```

### ❌ NICHT UNTERSTÜTZT (aktuell)

Die folgenden Patterns werden **NICHT** erkannt:

```
{basis}_podcast_{zeitstempel}_softsubs_thumb.jpg    ✗ (zu spezifisch)
{basis}_thumb.jpg                                    ✗ (falsches Pattern)
{name}.jpg                                           ✗ (kein erkanntes Pattern)
```

### 🔄 Automatische Generierung

Falls kein Thumbnail gefunden wird:
- App generiert automatisch Thumbnail aus Video bei t=3s
- Output: `{video_stem}_thumb.jpg` (im Video-Verzeichnis)
- Beispiel: `die-sonnenseite-der-klischees_podcast_20251111_205254_softsubs_thumb.jpg`

**Hinweis:** Generierte Thumbnails werden **nicht** beim nächsten Reload automatisch erkannt (siehe Limitations oben).

---

## Vollständiges Beispiel: Erkannte Dateien

Gegeben ein Video: `die-sonnenseite-der-klischees_podcast_20251111_205254_softsubs.mp4`

### Was die App findet:

```
✓ Video-Varianten:
  - die-sonnenseite-der-klischees_podcast_20251111_205254_softsubs.mp4
  - die-sonnenseite-der-klischees_podcast_20251111_205254_hardsubs.mp4

✓ Untertitel:
  - die-sonnenseite-der-klischees.srt                        (externe SRT)
  - die-sonnenseite-der-klischees_podcast_20251111_205254_softsubs.srt  (externe SRT)
  - [Container-SRT aus softsubs.mp4]                         (wird extrahiert)

✓ JSON:
  - die-sonnenseite-der-klischees_yt_profile.json

✓ Thumbnail:
  - die-sonnenseite-der-klischees_thumbnail.png              (Pattern 1)
  - die-sonnenseite-der-klischees_20251111_205254_thumbnail.png  (Pattern 1)
  - sample_*.png                                             (Pattern 2, beliebiger Name)
```

### Was die App NICHT findet:

```
✗ JSON:
  - Untitled_template_20251111_210806.json          (fehlt _yt_profile)
  - video.info.json                                 (altes Format)

✗ Thumbnail:
  - die-sonnenseite-der-klischees_podcast_20251111_205254_softsubs_thumb.jpg  (zu spezifisch)
  - thumb.jpg                                       (kein erkanntes Pattern)
  - my-thumbnail.png                                (kein erkanntes Pattern)
```

---

## Empfohlene Namenskonventionen

### Für manuelle Erstellung

**JSON-Metadaten:**
```
{video-basis}_yt_profile.json
```

**Thumbnail:**
```
{video-basis}_thumbnail.png
```

**Externe SRT:**
```
{video-basis}.srt
```

### Beispiel-Set (empfohlen):

```
mein-video_yt_profile.json              ← JSON-Metadaten
mein-video_thumbnail.png                ← Thumbnail (manuell erstellt)
mein-video.srt                          ← Externe SRT (optional)
mein-video_podcast_20251111_205254_softsubs.mp4   ← Video mit Container-SRT
mein-video_podcast_20251111_205254_hardsubs.mp4   ← Video mit eingebrannten UT
```

---

## Code-Referenzen

### Matching-Funktionen

```python
# app/matching.py

_extract_base_name(video_stem: str) -> str
# Extrahiert Basis-Namen (entfernt Suffixe + Zeitstempel)

find_yt_profile_json(video_path: str) -> Optional[str]
# Findet {basis}*_yt_profile.json

find_specialized_video_files(video_path: str) -> dict
# Findet {basis}*_softsubs.mp4 und {basis}*_hardsubs.mp4

find_sample_thumbnail(video_path: str) -> Optional[str]
# Findet {basis}*_thumbnail.png oder sample_*.png

find_all_matching_files(video_path: str, extensions: list) -> List[str]
# Präfix-Matching (erste 12 Zeichen) für beliebige Extensions
```

### Zentrale Funktion

```python
# app/companion.py

get_video_companion_files(video_path: str) -> dict
# Findet alle Companion-Dateien
# Returns: json_file, softsubs_file, hardsubs_file, srt_file, thumbnail_file
```

---

## Bekannte Probleme & TODOs

### ❌ Problem: Generierte Thumbnails werden nicht wiedererkannt

**Status:** Bug
**Beschreibung:** Wenn die App ein Thumbnail generiert (`*_softsubs_thumb.jpg`), wird es beim nächsten Reload nicht gefunden

**Ursache:** Pattern `{basis}*_thumbnail.png` matcht nicht `*_softsubs_thumb.jpg`

**Workaround:** Thumbnail manuell umbenennen zu `{basis}_thumbnail.png`

**TODO:**
- Thumbnail-Pattern erweitern um `*_thumb.jpg`
- Oder: Generierte Thumbnails mit korrektem Namen speichern

### ⚠️ Problem: JSON-Dateien mit falschem Namen

**Status:** User Error (aber häufig)
**Beschreibung:** Viele JSON-Dateien heißen `Untitled_template_*.json` statt `*_yt_profile.json`

**Ursache:** LLM-Prompt erzeugt falschen Dateinamen oder User benennt nicht um

**TODO:**
- LLM-Prompt-Template aktualisieren (siehe `docs/PROMPT_YT_METADATA.md`)
- Fallback-Pattern überlegen (z.B. `*.json` als letzte Option)?

---

## Änderungshistorie

### 2025-11-22 (Version 4.3.0)

- SRT-Upload-Logik überarbeitet: Profil-abhängig (`requires_srt`)
- SRT wird aus softsubs-Video extrahiert (korrektes Timing)
- `social_subtitled` lädt keine SRT hoch (Hardsubs)
- Neue Funktion: `extract_srt_from_video()` in uploader.py

### 2025-11-13 (Version 4.0.0)

- Initiale Dokumentation erstellt
- `_extract_base_name()` implementiert (iteratives Suffix-Entfernen)
- Thumbnail-Pattern `{basis}*_thumbnail.png` hinzugefügt
- Bug identifiziert: Generierte Thumbnails werden nicht wiedererkannt

---

**Nächste Schritte:**

1. Thumbnail-Pattern erweitern oder Generierungs-Namen anpassen
2. JSON-Fallback-Pattern evaluieren
3. Tests schreiben für alle Matching-Funktionen
