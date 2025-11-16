#!/usr/bin/env python3
"""
YouTube Upload Tool - Einstiegspunkt

Prüft Conda-Environment und startet GUI.
Fail Fast: Bricht sofort ab, wenn nicht im korrekten Environment.
"""

from app.config import check_environment
from app.gui_batch import run_app


def main():
    """Hauptfunktion: Environment-Check + GUI-Start."""
    # Fail Fast: Environment prüfen
    check_environment()

    # GUI starten
    print("Starte YouTube Upload Tool...")
    run_app()


if __name__ == "__main__":
    main()
