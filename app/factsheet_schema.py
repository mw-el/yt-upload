"""
JSON-Schema für die Validierung von .info.json-Dateien (Factsheets).
Definiert die erwartete Struktur für Video-Metadaten.
"""

import json
from jsonschema import validate, ValidationError
from typing import Dict, Any

# JSON-Schema für Factsheet-Dateien
FACTSHEET_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["title", "description"],
    "properties": {
        "title": {
            "type": "string",
            "minLength": 1,
            "maxLength": 100,
            "description": "Videotitel (max. 100 Zeichen)"
        },
        "description": {
            "type": "string",
            "description": "Videobeschreibung"
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 500,
            "description": "Video-Tags (max. 500)"
        },
        "category": {
            "type": "string",
            "description": "Kategorie-ID (z.B. '22' für People & Blogs)"
        },
        "language": {
            "type": "string",
            "pattern": "^[a-z]{2}$",
            "description": "Sprache (ISO 639-1, z.B. 'de', 'en')"
        },
        "chapters": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["time", "title"],
                "properties": {
                    "time": {
                        "type": "string",
                        "pattern": "^\\d{1,2}:\\d{2}(:\\d{2})?$",
                        "description": "Zeitstempel (z.B. '0:00' oder '1:23:45')"
                    },
                    "title": {
                        "type": "string",
                        "minLength": 1,
                        "description": "Kapiteltitel"
                    }
                }
            },
            "description": "Video-Kapitel"
        },
        "thumbnail": {
            "type": "string",
            "description": "Pfad zum Thumbnail-Bild (optional)"
        }
    },
    "additionalProperties": True
}


def validate_factsheet(data: Dict[str, Any]) -> tuple[bool, str]:
    """
    Validiert Factsheet-Daten gegen das JSON-Schema.

    Args:
        data: Dictionary mit Factsheet-Daten

    Returns:
        Tuple (is_valid, error_message)
        - is_valid: True wenn valide, False bei Fehler
        - error_message: Fehlermeldung oder leerer String
    """
    try:
        validate(instance=data, schema=FACTSHEET_SCHEMA)
        return True, ""
    except ValidationError as e:
        error_msg = f"Schema-Validierung fehlgeschlagen: {e.message}"
        if e.path:
            error_msg += f"\nPfad: {' -> '.join(str(p) for p in e.path)}"
        return False, error_msg
    except Exception as e:
        return False, f"Unerwarteter Fehler bei Validierung: {str(e)}"


def load_and_validate_factsheet(file_path: str) -> tuple[bool, Dict[str, Any] | None, str]:
    """
    Lädt und validiert eine Factsheet-Datei.

    Args:
        file_path: Pfad zur .info.json-Datei

    Returns:
        Tuple (is_valid, data, error_message)
        - is_valid: True wenn erfolgreich geladen und valide
        - data: Dictionary mit Factsheet-Daten oder None
        - error_message: Fehlermeldung oder leerer String
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        is_valid, error_msg = validate_factsheet(data)
        if is_valid:
            return True, data, ""
        else:
            return False, None, error_msg

    except FileNotFoundError:
        return False, None, f"Datei nicht gefunden: {file_path}"
    except json.JSONDecodeError as e:
        return False, None, f"JSON-Parsing-Fehler: {str(e)}"
    except Exception as e:
        return False, None, f"Fehler beim Laden: {str(e)}"
