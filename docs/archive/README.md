# Archiv: Veraltete Dateien

Dieses Verzeichnis enthält veraltete Dateien aus früheren Versionen des YouTube Upload Tools.

---

## Archivierte Dateien

### `gui.py` (Legacy Single-Video GUI)
- **Version:** 1.0 - 2.0
- **Grund:** Ersetzt durch `gui_batch.py` (Batch-Upload-GUI) in Version 3.0
- **Status:** Nicht mehr verwendet

### `example.info.json` & `example_minimal.info.json`
- **Version:** 1.0 - 3.0
- **Grund:** Altes JSON-Format (Root-Level `title`, `description`)
- **Ersetzt durch:** Neues Format mit `snippet`, `status`, etc. (siehe `docs/PROMPT_YT_METADATA.md`)
- **Status:** Nicht kompatibel mit aktuellem Schema

### `DEVLOG.md`
- **Version:** 1.0 - 3.0
- **Grund:** Veraltet, nicht mehr aktuell gehalten
- **Ersetzt durch:** `CHANGELOG.md` (strukturierter)
- **Status:** Historisch

---

## Warum archiviert?

Diese Dateien wurden archiviert statt gelöscht, um:
1. **Historie zu bewahren** - Nachvollziehbarkeit früherer Design-Entscheidungen
2. **Referenz zu ermöglichen** - Fallback wenn etwas fehlt
3. **Vermeidung von Verwirrung** - Klar trennen zwischen aktiv und veraltet

---

**Hinweis:** Dateien in diesem Verzeichnis werden nicht mehr gewartet und funktionieren möglicherweise nicht mit der aktuellen Version.

**Aktuelle Version:** 4.0.0
**Archiviert am:** 2025-11-13
