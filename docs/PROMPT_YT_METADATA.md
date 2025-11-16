# LLM-Prompt für YouTube-Metadaten-Generierung

## Übersicht

Dieser Prompt wird verwendet, um aus SRT-Transkripten strukturierte YouTube-Metadaten zu generieren.

**Ausgabe-Dateiname:** `{basename}_yt_profile.json`

---

## Prompt-Template

```
Du bist Redaktor und Metadaten-Generator für YouTube.
Schreibe Schweizer Standarddeutsch (de-CH).
Stil: klar, konkret, ohne Füllfloskeln, ohne Emojis.

Deine Aufgabe:
Erzeuge aus dem gegebenen SRT-Transkript ein vollständiges JSON-Factsheet
für den YouTube-Upload.

-------------------------------------
AUSGABE-DATEINAME
-------------------------------------
Die generierte JSON-Datei MUSS folgenden Namen haben:
{basename}_yt_profile.json

Beispiel:
- Video: warum-chatgpt-nie-gleich_podcast_20251103_085932_softsubs.mp4
- JSON:  warum-chatgpt-nie-gleich_yt_profile.json

(Zeitstempel und Suffixe wie _softsubs, _hardsubs werden entfernt)

-------------------------------------
REGELN UND ANFORDERUNGEN
-------------------------------------
- Gib AUSSCHLIESSLICH gültiges JSON aus – ohne Kommentare, ohne Markdown.
- Keine Fakten erfinden. Verwende nur Transkript + Metadaten.
- Sprache: de-CH.
- snippet.title: ≤ 80 Zeichen, klar, ohne Clickbait.
- snippet.description_short: genau 2 Sätze.
- snippet.description_bullets: 5–8 kurze Punkte.
- chapters: sinnvolle inhaltliche Abschnitte; beginne bei 00:00; Format MM:SS.
- snippet.tags: 10–15, nur Kleinbuchstaben, keine Dubletten.
- snippet.hashtags: 3–5, beginnen mit #.
- snippet.categoryId: Standard "22", ausser Thema verlangt spezifische Kategorie.
- status.privacyStatus: "unlisted" (für Embedding), "public" (für YouTube), "private" (intern)
- captions.file: Pfad zur SRT-Datei (relativ oder absolut)
- thumbnail.file: null (wird automatisch generiert), oder Pfad zu sample_*.png
- thumbnail.autogenerate_if_missing: true
- thumbnail.autogenerate_frame_sec: 3 (Standard: 3 Sekunden)
- embed_params: YouTube-Embed-Parameter (optional)
- playlist.title: nur setzen, wenn Seriencharakter klar erkennbar.
- notes: kurzer technischer Hinweis oder leerer String.

-------------------------------------
JSON-SCHEMA
-------------------------------------
{
  "source_file": "string (Basis-Dateiname ohne Erweiterung)",
  "language": "de-CH",
  "snippet": {
    "title": "string (≤ 80 Zeichen)",
    "description_short": "string (2 Sätze)",
    "description_bullets": ["string", ...],
    "tags": ["string", ...],
    "hashtags": ["#string", ...],
    "categoryId": "22"
  },
  "status": {
    "privacyStatus": "unlisted|public|private",
    "embeddable": true,
    "publishAt": null,
    "madeForKids": false
  },
  "chapters": [
    {
      "timecode": "MM:SS",
      "title": "string"
    }
  ],
  "captions": {
    "file": "./path/to/file.srt",
    "language": "de-CH"
  },
  "thumbnail": {
    "file": null,
    "autogenerate_if_missing": true,
    "autogenerate_frame_sec": 3
  },
  "embed_params": {
    "modestbranding": "1",
    "rel": "0",
    "controls": "1",
    "playsinline": "1"
  },
  "playlist": {
    "create_if_missing": false,
    "title": "string oder null",
    "id": null
  },
  "notes": "string"
}

-------------------------------------
KONTEXT FÜR DIESES VIDEO
-------------------------------------
- basename: {{BASENAME}}
- duration_sec: {{DURATION_SEC}}
- recorded_date: {{RECORDED_DATE}}
- srt_path: {{SRT_PATH}}
- video_path: {{VIDEO_PATH}}
- default_tags: ["podcast","schreiben","ki","schreibszene"]
- site_url: "https://schreibszene.ch"

-------------------------------------
EINGABE (Transkript im SRT-Format)
-------------------------------------

{{SRT_TEXT}}
```

---

## Datei-Struktur im Verzeichnis

Typische Dateistruktur nach Verarbeitung:

```
my-video_podcast_20251103_085932_softsubs.mp4   # Video mit Container-SRT
my-video_podcast_20251103_085932_hardsubs.mp4   # Video mit eingebrannten Untertiteln
my-video_yt_profile.json                        # ← Generiert von LLM
my-video.srt                                    # Externe SRT (falls vorhanden)
sample_MyVideo_20251102_150059.png              # Thumbnail nach Textanimation
```

**Wichtig:** Das Tool sucht automatisch nach:
- `*_yt_profile.json` für Metadaten
- `*_softsubs.mp4` für Video mit Container-SRT
- `*_hardsubs.mp4` für Video mit eingebrannten Untertiteln
- `*.srt` für externe Untertitel
- `sample_*.png` für Thumbnail

---

## YouTube-Kategorien

Häufig verwendete Kategorie-IDs:

- `22`: People & Blogs (Standard)
- `27`: Education
- `28`: Science & Technology
- `24`: Entertainment
- `10`: Music

[Vollständige Liste](https://developers.google.com/youtube/v3/docs/videoCategories/list)

---

## Upload-Profile (im Tool)

Das Upload-Tool unterstützt mehrere Profile, die jeweils unterschiedliche Anforderungen haben:

1. **neutral_embed** (unlisted, für Website-Embedding)
   - Benötigt: JSON
   - Optional: SRT

2. **public_youtube** (public, SEO-optimiert)
   - Benötigt: JSON, SRT

3. **social_subtitled** (private, mit eingebrannten Untertiteln)
   - Benötigt: JSON, hardsubs-Video
   - Keine SRT nötig (Untertitel sind eingebrannt)

**Hinweis:** Die JSON-Datei wird für ALLE Profile verwendet. Die spezifischen Einstellungen
(privacyStatus, embeddable, etc.) werden vom Tool basierend auf dem gewählten Profil überschrieben.

---

## Beispiel-Ausgabe

```json
{
  "source_file": "warum-chatgpt-nie-gleich",
  "language": "de-CH",
  "snippet": {
    "title": "Warum ChatGPT nie die gleiche Antwort zweimal gibt",
    "description_short": "KI-Systeme liefern bei gleichen Prompts unterschiedliche Ergebnisse. Dieser Beitrag erklärt die technischen Gründe dahinter: Temperatur-Parameter und Hardware-bedingte Rundungsfehler.",
    "description_bullets": [
      "Mathematik ist deterministisch, KI-Modelle bestehen aus Mathematik – trotzdem variieren die Ergebnisse.",
      "Die Temperatur steuert die Vielfalt: höhere Werte führen zu mehr Abwechslung durch Zufallsauswahl.",
      "Fliesskomma-Arithmetik und Hardware-Eigenschaften beeinflussen die Berechnungen auch bei Temperatur 0.",
      "Grafikkarten führen Berechnungen nicht immer in der gleichen Reihenfolge durch.",
      "Kleine Werte gehen bei der Rundung verloren, wenn sie mit sehr grossen Zahlen verrechnet werden.",
      "Tests zeigen: Bei 1000 Durchläufen mit Temperatur 0 entstehen 80 verschiedene Textvarianten.",
      "Strenge Kontrolle der Berechnungsreihenfolge macht Modelle zuverlässiger, aber langsamer."
    ],
    "tags": [
      "chatgpt",
      "ki",
      "künstliche intelligenz",
      "temperatur",
      "fliesskomma",
      "rundungsfehler",
      "hardware",
      "grafikkarte",
      "determinismus",
      "wahrscheinlichkeit",
      "algorithmus",
      "maschinelles lernen",
      "luxuswissen",
      "schreibszene",
      "technische erklärung"
    ],
    "hashtags": [
      "#ChatGPT",
      "#KünstlicheIntelligenz",
      "#TechnikErklärt",
      "#Schreibszene"
    ],
    "categoryId": "28"
  },
  "status": {
    "privacyStatus": "unlisted",
    "embeddable": true,
    "publishAt": null,
    "madeForKids": false
  },
  "chapters": [
    {
      "timecode": "00:00",
      "title": "Einleitung: Warum unterschiedliche Ergebnisse?"
    },
    {
      "timecode": "00:44",
      "title": "Mathematik ist deterministisch"
    },
    {
      "timecode": "01:55",
      "title": "Drei verschiedene Headlines – wie kann das sein?"
    }
  ],
  "captions": {
    "file": "./warum-chatgpt-nie-gleich.srt",
    "language": "de-CH"
  },
  "thumbnail": {
    "file": null,
    "autogenerate_if_missing": true,
    "autogenerate_frame_sec": 3
  },
  "embed_params": {
    "modestbranding": "1",
    "rel": "0",
    "controls": "1",
    "playsinline": "1"
  },
  "playlist": {
    "create_if_missing": false,
    "title": "Luxuswissen KI",
    "id": null
  },
  "notes": "Erklärvideo zur technischen Funktionsweise von KI-Systemen, basierend auf Forschung von Thinking Machines Lab (Mira Murati). Zielgruppe: technisch interessierte Laien."
}
```

---

## Integration im Upload-Tool

Das Tool verwendet folgende Logik:

1. **Video-Auswahl:** User wählt Video-Datei(en)
2. **Automatische Suche:** Tool sucht nach `*_yt_profile.json`, `*.srt`, `*_softsubs.mp4`, `*_hardsubs.mp4`, `sample_*.png`
3. **Fehlende Dateien:**
   - Keine JSON → Fehler (manuell nachliefern)
   - Keine SRT → Extraktion aus softsubs-Video versuchen
   - Kein Thumbnail → Aus Video bei t=3s generieren
4. **Profil-Auswahl:** User wählt Upload-Profile (neutral_embed, public_youtube, social_subtitled)
5. **Upload:** Für jedes Profil separater Upload mit entsprechenden Einstellungen

---

**Letzte Aktualisierung:** 2025-11-13
**Version:** 1.0
