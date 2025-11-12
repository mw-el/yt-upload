"""
YouTube-Upload-Schnittstelle.
Implementiert Video-, Untertitel- und Thumbnail-Upload zu YouTube.
"""

import os
from typing import Dict, Any, Tuple, Optional, Callable
from pathlib import Path

from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from app.auth import create_youtube_client, AuthError
from app.config import CLIENT_SECRETS_PATH, TOKEN_PATH


class UploadError(Exception):
    """Fehler beim YouTube-Upload."""
    pass


class UploadResult:
    """Ergebnis eines erfolgreichen Uploads."""

    def __init__(self, video_id: str, title: str):
        self.video_id = video_id
        self.title = title

    @property
    def watch_url(self) -> str:
        """Öffentliche Watch-URL."""
        return f"https://www.youtube.com/watch?v={self.video_id}"

    @property
    def embed_url(self) -> str:
        """Embed-URL für iframes."""
        return f"https://www.youtube.com/embed/{self.video_id}"

    def __str__(self) -> str:
        return (
            f"Upload erfolgreich!\n"
            f"Video-ID: {self.video_id}\n"
            f"Titel: {self.title}\n"
            f"Watch: {self.watch_url}\n"
            f"Embed: {self.embed_url}"
        )


def _prepare_video_metadata(
    factsheet_data: Dict[str, Any],
    profile_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Bereitet Video-Metadaten für YouTube API vor.

    Args:
        factsheet_data: Validierte Metadaten aus .info.json
        profile_data: Upload-Profil mit YouTube-Einstellungen

    Returns:
        Dictionary mit YouTube-konformen Metadaten
    """
    # Basis-Snippet aus Factsheet
    snippet = {
        'title': factsheet_data['title'],
        'description': factsheet_data.get('description', ''),
    }

    # Tags hinzufügen (falls vorhanden)
    if 'tags' in factsheet_data and factsheet_data['tags']:
        snippet['tags'] = factsheet_data['tags']

    # Kategorie aus Profil oder Factsheet
    category_id = profile_data.get('snippet', {}).get('categoryId')
    if not category_id and 'category' in factsheet_data:
        category_id = factsheet_data['category']
    if category_id:
        snippet['categoryId'] = str(category_id)

    # Sprache (falls vorhanden)
    if 'language' in factsheet_data:
        snippet['defaultLanguage'] = factsheet_data['language']

    # Kapitel in Description einfügen (falls vorhanden)
    if 'chapters' in factsheet_data and factsheet_data['chapters']:
        chapters_text = "\n\n⏱ Kapitel:\n"
        for chapter in factsheet_data['chapters']:
            chapters_text += f"{chapter['time']} - {chapter['title']}\n"
        snippet['description'] += chapters_text

    # Status aus Profil
    status = profile_data.get('status', {})

    # Kombiniere alles
    body = {
        'snippet': snippet,
        'status': status
    }

    return body


def upload(
    video_path: str,
    srt_path: Optional[str],
    factsheet_data: Dict[str, Any],
    profile_data: Dict[str, Any],
    progress_callback: Optional[Callable[[float], None]] = None
) -> UploadResult:
    """
    Lädt Video mit Metadaten und Untertiteln zu YouTube hoch.

    Args:
        video_path: Pfad zur Video-Datei
        srt_path: Pfad zur SRT-Datei (optional)
        factsheet_data: Validierte Metadaten aus .info.json
        profile_data: Upload-Profil mit YouTube-Einstellungen
        progress_callback: Optional callback für Upload-Fortschritt (0.0-1.0)

    Returns:
        UploadResult mit Video-ID und URLs

    Raises:
        UploadError: Bei Upload-Fehlern
        AuthError: Bei Authentifizierungsfehlern
    """

    # ===========================
    # 1. Authentifizierung
    # ===========================
    try:
        print("🔐 Authentifiziere mit YouTube...")
        youtube = create_youtube_client(CLIENT_SECRETS_PATH, TOKEN_PATH)
        print("✓ Authentifizierung erfolgreich")
    except AuthError as e:
        raise UploadError(f"Authentifizierung fehlgeschlagen:\n{str(e)}")

    # ===========================
    # 2. Video-Metadaten vorbereiten
    # ===========================
    print("📋 Bereite Metadaten vor...")
    body = _prepare_video_metadata(factsheet_data, profile_data)
    print(f"   Titel: {body['snippet']['title']}")
    print(f"   Status: {body['status'].get('privacyStatus', 'N/A')}")

    # ===========================
    # 3. Video hochladen
    # ===========================
    try:
        print(f"📤 Lade Video hoch: {Path(video_path).name}")

        # Media-Upload vorbereiten
        media = MediaFileUpload(
            video_path,
            chunksize=1024*1024,  # 1 MB chunks
            resumable=True
        )

        # Upload-Request erstellen
        request = youtube.videos().insert(
            part='snippet,status',
            body=body,
            media_body=media
        )

        # Upload durchführen
        response = None
        last_progress = 0

        while response is None:
            status, response = request.next_chunk()
            if status:
                progress = status.progress()
                if progress_callback:
                    progress_callback(progress)

                # Zeige Fortschritt nur alle 10%
                if int(progress * 10) > int(last_progress * 10):
                    print(f"   Fortschritt: {int(progress * 100)}%")
                    last_progress = progress

        video_id = response['id']
        print(f"✓ Video hochgeladen! ID: {video_id}")

    except HttpError as e:
        error_details = e.error_details if hasattr(e, 'error_details') else str(e)
        raise UploadError(f"YouTube API-Fehler beim Video-Upload:\n{error_details}")
    except FileNotFoundError:
        raise UploadError(f"Video-Datei nicht gefunden: {video_path}")
    except Exception as e:
        raise UploadError(f"Unerwarteter Fehler beim Video-Upload: {str(e)}")

    # ===========================
    # 4. Untertitel hochladen (falls vorhanden)
    # ===========================
    if srt_path and Path(srt_path).exists():
        try:
            print(f"📝 Lade Untertitel hoch: {Path(srt_path).name}")

            language = factsheet_data.get('language', 'de')

            caption_body = {
                'snippet': {
                    'videoId': video_id,
                    'language': language,
                    'name': f'Untertitel ({language})',
                    'isDraft': False
                }
            }

            media = MediaFileUpload(srt_path, mimetype='application/x-subrip')

            youtube.captions().insert(
                part='snippet',
                body=caption_body,
                media_body=media
            ).execute()

            print(f"✓ Untertitel hochgeladen (Sprache: {language})")

        except HttpError as e:
            print(f"⚠ Warnung: Untertitel konnten nicht hochgeladen werden: {e}")
        except Exception as e:
            print(f"⚠ Warnung: Unerwarteter Fehler bei Untertiteln: {e}")

    # ===========================
    # 5. Thumbnail hochladen (falls vorhanden)
    # ===========================
    if 'thumbnail' in factsheet_data:
        thumbnail_path = factsheet_data['thumbnail']
        if Path(thumbnail_path).exists():
            try:
                print(f"🖼 Lade Thumbnail hoch: {Path(thumbnail_path).name}")

                media = MediaFileUpload(thumbnail_path, mimetype='image/jpeg')

                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=media
                ).execute()

                print("✓ Thumbnail hochgeladen")

            except HttpError as e:
                print(f"⚠ Warnung: Thumbnail konnte nicht hochgeladen werden: {e}")
            except Exception as e:
                print(f"⚠ Warnung: Unerwarteter Fehler bei Thumbnail: {e}")

    # ===========================
    # Erfolgreich abgeschlossen
    # ===========================
    return UploadResult(
        video_id=video_id,
        title=factsheet_data.get('title', 'Unbekannter Titel')
    )


def validate_upload_prerequisites() -> Tuple[bool, str]:
    """
    Prüft, ob alle Voraussetzungen für Upload erfüllt sind.

    Returns:
        Tuple (is_ready, error_message)
    """
    client_secrets = Path(CLIENT_SECRETS_PATH)

    if not client_secrets.exists():
        return False, (
            f"OAuth2-Credentials nicht gefunden: {CLIENT_SECRETS_PATH}\n\n"
            f"Erstelle OAuth2-Credentials:\n"
            f"1. Gehe zu https://console.cloud.google.com/apis/credentials\n"
            f"2. Erstelle ein Projekt\n"
            f"3. Aktiviere YouTube Data API v3\n"
            f"4. Erstelle OAuth2-Credentials (Desktop-App)\n"
            f"5. Lade client_secrets.json herunter\n"
            f"6. Speichere als: {CLIENT_SECRETS_PATH}\n\n"
            f"Oder setze YOUTUBE_CLIENT_SECRETS_PATH in .env"
        )

    return True, ""
