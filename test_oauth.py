#!/usr/bin/env python3
"""
Test-Script für OAuth2-Authentifizierung und YouTube-Connection.
Prüft, ob die OAuth-Setup korrekt ist, ohne tatsächlich ein Video hochzuladen.
"""

import sys
from pathlib import Path

# Prüfe Environment
from app.config import check_environment
check_environment()

from app.auth import create_youtube_client, AuthError
from app.config import CLIENT_SECRETS_PATH, TOKEN_PATH

def test_oauth():
    """Testet OAuth2-Authentifizierung."""
    print("=" * 60)
    print("YouTube OAuth2 Test")
    print("=" * 60)
    print()

    # Prüfe, ob client_secrets.json existiert
    client_secrets = Path(CLIENT_SECRETS_PATH)
    if not client_secrets.exists():
        print(f"❌ FEHLER: client_secrets.json nicht gefunden!")
        print(f"   Erwartet: {CLIENT_SECRETS_PATH}")
        print()
        print("📖 Siehe docs/README_OAUTH.md für Setup-Anleitung")
        return False

    print(f"✓ client_secrets.json gefunden: {CLIENT_SECRETS_PATH}")
    print()

    # Versuche YouTube-Client zu erstellen
    try:
        print("🔐 Authentifiziere mit YouTube...")
        print("   (Browser öffnet sich beim ersten Mal)")
        print()

        youtube = create_youtube_client(CLIENT_SECRETS_PATH, TOKEN_PATH)

        print("✓ Authentifizierung erfolgreich!")
        print()

        # Test: Hole Channel-Info
        print("🔍 Teste API-Zugriff...")
        request = youtube.channels().list(
            part="snippet,contentDetails,statistics",
            mine=True
        )
        response = request.execute()

        if "items" in response and len(response["items"]) > 0:
            channel = response["items"][0]
            print(f"✓ API-Zugriff funktioniert!")
            print()
            print(f"📺 Kanal-Info:")
            print(f"   Name: {channel['snippet']['title']}")
            print(f"   ID: {channel['id']}")
            print(f"   Videos: {channel['statistics'].get('videoCount', 'N/A')}")
            print(f"   Abonnenten: {channel['statistics'].get('subscriberCount', 'N/A')}")
            print()
        else:
            print("⚠ Warnung: Keine Kanal-Info erhalten")
            print("   OAuth funktioniert, aber möglicherweise keine Kanäle vorhanden")
            print()

        # Token-Info
        token_file = Path(TOKEN_PATH)
        if token_file.exists():
            print(f"💾 Token gespeichert: {TOKEN_PATH}")
            print("   Bei zukünftigen Starts kein Browser-Login mehr nötig")
        print()

        print("=" * 60)
        print("✅ OAuth2-Setup ist korrekt!")
        print("=" * 60)
        print()
        print("Du kannst jetzt Videos hochladen:")
        print("  ./start.sh")
        print()

        return True

    except AuthError as e:
        print(f"❌ Authentifizierungsfehler:")
        print(f"   {str(e)}")
        print()
        print("📖 Siehe docs/README_OAUTH.md für Hilfe")
        return False

    except Exception as e:
        print(f"❌ Unerwarteter Fehler:")
        print(f"   {str(e)}")
        print()
        print("💡 Mögliche Ursachen:")
        print("   - Falsche Scopes in client_secrets.json")
        print("   - YouTube Data API v3 nicht aktiviert")
        print("   - Netzwerkprobleme")
        print()
        return False


if __name__ == "__main__":
    success = test_oauth()
    sys.exit(0 if success else 1)
