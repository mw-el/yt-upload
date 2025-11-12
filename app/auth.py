"""
OAuth2-Authentifizierung für YouTube API.
Verwaltet Credentials, Token-Refresh und API-Client-Erstellung.
"""

import os
import pickle
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


# OAuth2-Scopes für YouTube
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube',
    'https://www.googleapis.com/auth/youtube.force-ssl'
]


class AuthError(Exception):
    """Fehler bei der Authentifizierung."""
    pass


class YouTubeAuth:
    """Verwaltet YouTube OAuth2-Authentifizierung."""

    def __init__(self, client_secrets_path: str, token_path: str):
        """
        Args:
            client_secrets_path: Pfad zur client_secrets.json
            token_path: Pfad zur Token-Datei (wird erstellt)
        """
        self.client_secrets_path = Path(client_secrets_path)
        self.token_path = Path(token_path)
        self.credentials: Optional[Credentials] = None

    def authenticate(self) -> Credentials:
        """
        Führt OAuth2-Authentifizierung durch.
        Lädt bestehenden Token oder startet OAuth2-Flow.

        Returns:
            Google OAuth2 Credentials

        Raises:
            AuthError: Bei Authentifizierungsfehlern
        """
        # Prüfe, ob client_secrets.json existiert
        if not self.client_secrets_path.exists():
            raise AuthError(
                f"OAuth2-Credentials nicht gefunden: {self.client_secrets_path}\n\n"
                f"Erstelle OAuth2-Credentials in Google Cloud Console:\n"
                f"1. Gehe zu https://console.cloud.google.com/apis/credentials\n"
                f"2. Erstelle ein Projekt (falls noch nicht vorhanden)\n"
                f"3. Aktiviere YouTube Data API v3\n"
                f"4. Erstelle OAuth2-Credentials (Desktop-App)\n"
                f"5. Lade client_secrets.json herunter\n"
                f"6. Speichere als: {self.client_secrets_path}"
            )

        # Versuche bestehenden Token zu laden
        if self.token_path.exists():
            try:
                with open(self.token_path, 'rb') as token_file:
                    self.credentials = pickle.load(token_file)
            except Exception as e:
                print(f"⚠ Warnung: Token konnte nicht geladen werden: {e}")
                self.credentials = None

        # Prüfe, ob Token valide ist
        if self.credentials and self.credentials.valid:
            return self.credentials

        # Token erneuern, falls abgelaufen
        if self.credentials and self.credentials.expired and self.credentials.refresh_token:
            try:
                print("🔄 Token ist abgelaufen, erneuere...")
                self.credentials.refresh(Request())
                self._save_token()
                print("✓ Token erfolgreich erneuert")
                return self.credentials
            except Exception as e:
                print(f"⚠ Token-Refresh fehlgeschlagen: {e}")
                self.credentials = None

        # Starte OAuth2-Flow (Browser öffnet sich)
        return self._run_oauth_flow()

    def _run_oauth_flow(self) -> Credentials:
        """
        Startet OAuth2-Flow im Browser.

        Returns:
            Google OAuth2 Credentials

        Raises:
            AuthError: Bei Fehlern im OAuth2-Flow
        """
        try:
            print("🔐 Starte OAuth2-Authentifizierung...")
            print("    Browser öffnet sich gleich...")
            print("    Bitte erlaube Zugriff auf dein YouTube-Konto.")

            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.client_secrets_path),
                SCOPES
            )

            # Starte lokalen Server für OAuth-Callback
            self.credentials = flow.run_local_server(
                port=8080,
                prompt='consent',
                success_message='Authentifizierung erfolgreich! Du kannst dieses Fenster schließen.'
            )

            # Speichere Token für zukünftige Verwendung
            self._save_token()
            print("✓ Authentifizierung erfolgreich!")

            return self.credentials

        except Exception as e:
            raise AuthError(f"OAuth2-Flow fehlgeschlagen: {str(e)}")

    def _save_token(self):
        """Speichert Token in Datei."""
        try:
            # Erstelle Verzeichnis falls nötig
            self.token_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.token_path, 'wb') as token_file:
                pickle.dump(self.credentials, token_file)

            print(f"💾 Token gespeichert: {self.token_path}")

        except Exception as e:
            print(f"⚠ Warnung: Token konnte nicht gespeichert werden: {e}")

    def get_youtube_client(self):
        """
        Erstellt authentifizierten YouTube API-Client.

        Returns:
            YouTube API Resource

        Raises:
            AuthError: Bei Authentifizierungsfehlern
        """
        if not self.credentials:
            self.authenticate()

        try:
            youtube = build('youtube', 'v3', credentials=self.credentials)
            return youtube
        except Exception as e:
            raise AuthError(f"YouTube-Client konnte nicht erstellt werden: {str(e)}")


def create_youtube_client(client_secrets_path: str, token_path: str):
    """
    Hilfsfunktion zum Erstellen eines authentifizierten YouTube-Clients.

    Args:
        client_secrets_path: Pfad zur client_secrets.json
        token_path: Pfad zur Token-Datei

    Returns:
        YouTube API Resource

    Raises:
        AuthError: Bei Authentifizierungsfehlern
    """
    auth = YouTubeAuth(client_secrets_path, token_path)
    return auth.get_youtube_client()
