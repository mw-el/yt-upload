"""
YouTube-Upload-Schnittstelle.
Implementiert Video-, Untertitel- und Thumbnail-Upload zu YouTube.
"""

import os
import subprocess
import tempfile
from typing import Dict, Any, Tuple, Optional, Callable, List
from pathlib import Path

from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from app.auth import create_youtube_client, AuthError
from app.config import CLIENT_SECRETS_PATH, TOKEN_PATH
from app.source_map import update_source_folder


def extract_srt_from_video(video_path: str) -> Optional[str]:
    """
    Extrahiert SRT-Untertitel aus einem Video-Container (softsubs).

    Args:
        video_path: Pfad zum Video mit eingebetteten Untertiteln

    Returns:
        Pfad zur extrahierten SRT-Datei oder None bei Fehler
    """
    video_file = Path(video_path)
    if not video_file.exists():
        return None

    # Erstelle temporäre SRT-Datei im selben Verzeichnis
    srt_path = video_file.parent / f"{video_file.stem}_extracted.srt"

    try:
        # FFmpeg-Befehl zum Extrahieren der ersten Untertitelspur
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-map", "0:s:0",
            "-c:s", "srt",
            str(srt_path)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0 and srt_path.exists():
            return str(srt_path)
        else:
            # Keine Untertitelspur vorhanden oder Fehler
            return None

    except subprocess.TimeoutExpired:
        return None
    except FileNotFoundError:
        # FFmpeg nicht installiert
        return None
    except Exception:
        return None


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
    snippet_source = factsheet_data.get('snippet') or {}
    legacy_title = factsheet_data.get('title')
    title = snippet_source.get('title') or legacy_title

    if not title:
        raise UploadError("Factsheet enthält keinen Titel (snippet.title).")

    description_parts: List[str] = []
    if snippet_source.get('description_short'):
        description_parts.append(snippet_source['description_short'].strip())

    bullets = snippet_source.get('description_bullets') or []
    bullet_lines = [f"- {item.strip()}" for item in bullets if isinstance(item, str) and item.strip()]
    if bullet_lines:
        description_parts.append("\n".join(bullet_lines))

    if snippet_source.get('description'):
        description_parts.append(snippet_source['description'].strip())
    elif factsheet_data.get('description'):
        description_parts.append(str(factsheet_data['description']).strip())

    hashtags = snippet_source.get('hashtags') or []
    hashtag_line = " ".join(tag.strip() for tag in hashtags if isinstance(tag, str) and tag.strip())
    if hashtag_line:
        description_parts.append(hashtag_line)

    description = "\n\n".join(part for part in description_parts if part).strip()
    if not description:
        description = title

    snippet = {
        'title': title,
        'description': description
    }

    tags = snippet_source.get('tags') or factsheet_data.get('tags')
    if tags:
        snippet['tags'] = tags

    category_id = (
        snippet_source.get('categoryId')
        or profile_data.get('snippet', {}).get('categoryId')
        or factsheet_data.get('categoryId')
        or factsheet_data.get('category')
    )
    if category_id:
        snippet['categoryId'] = str(category_id)

    language = factsheet_data.get('language')
    if language:
        snippet['defaultLanguage'] = language
        snippet['defaultAudioLanguage'] = language

    if factsheet_data.get('chapters'):
        chapters_text = "\n\n⏱ Kapitel:\n"
        for chapter in factsheet_data['chapters']:
            timecode = chapter.get('timecode') or chapter.get('time')
            chapter_title = chapter.get('title')
            if timecode and chapter_title:
                chapters_text += f"{timecode} - {chapter_title}\n"
        snippet['description'] = (snippet['description'] + chapters_text).strip()

    status = {}
    status.update(factsheet_data.get('status', {}))
    status.update(profile_data.get('status', {}))

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
    progress_callback: Optional[Callable[[float], None]] = None,
    status_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
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

    def emit(event: str, **payload):
        if status_callback:
            status_callback(event, payload)

    # ===========================
    # 1. Authentifizierung
    # ===========================
    try:
        emit("auth_start")
        print("🔐 Authentifiziere mit YouTube...")
        youtube = create_youtube_client(CLIENT_SECRETS_PATH, TOKEN_PATH)
        print("✓ Authentifizierung erfolgreich")
        emit("auth_success")
    except AuthError as e:
        raise UploadError(f"Authentifizierung fehlgeschlagen:\n{str(e)}")

    # ===========================
    # 2. Video-Metadaten vorbereiten
    # ===========================
    print("📋 Bereite Metadaten vor...")
    body = _prepare_video_metadata(factsheet_data, profile_data)
    print(f"   Titel: {body['snippet']['title']}")
    print(f"   Status: {body['status'].get('privacyStatus', 'N/A')}")
    emit(
        "metadata_ready",
        title=body['snippet']['title'],
        status=body['status'].get('privacyStatus')
    )

    # ===========================
    # 3. Video hochladen
    # ===========================
    try:
        emit("upload_start", filename=Path(video_path).name)
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
        emit("upload_success", video_id=video_id)
        print(f"✓ Video hochgeladen! ID: {video_id}")

    except HttpError as e:
        error_details = e.error_details if hasattr(e, 'error_details') else str(e)
        raise UploadError(f"YouTube API-Fehler beim Video-Upload:\n{error_details}")
    except FileNotFoundError:
        raise UploadError(f"Video-Datei nicht gefunden: {video_path}")
    except Exception as e:
        raise UploadError(f"Unerwarteter Fehler beim Video-Upload: {str(e)}")

    # ===========================
    # 4. Untertitel hochladen (falls Profil requires_srt=true)
    # ===========================
    # Hardsubs-Profile (requires_srt=false) brauchen keine separate SRT-Datei
    requires_srt = profile_data.get('requires_srt', True)

    if requires_srt and srt_path and Path(srt_path).exists():
        try:
            emit("captions_start", filename=Path(srt_path).name)
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

            emit("captions_success", language=language)
            print(f"✓ Untertitel hochgeladen (Sprache: {language})")

        except HttpError as e:
            emit("captions_error", message=str(e))
            print(f"⚠ Warnung: Untertitel konnten nicht hochgeladen werden: {e}")
        except Exception as e:
            emit("captions_error", message=str(e))
            print(f"⚠ Warnung: Unerwarteter Fehler bei Untertiteln: {e}")

    # ===========================
    # 5. Thumbnail hochladen (falls vorhanden)
    # ===========================
    thumbnail_config = factsheet_data.get('thumbnail')
    thumbnail_path = None
    if isinstance(thumbnail_config, dict):
        thumbnail_path = thumbnail_config.get('file')
    else:
        thumbnail_path = thumbnail_config

    if thumbnail_path:
        thumb_file = Path(thumbnail_path)
        if not thumb_file.is_absolute():
            thumb_file = Path(video_path).parent / thumb_file

        if thumb_file.exists():
            try:
                emit("thumbnail_start", filename=thumb_file.name)
                print(f"🖼 Lade Thumbnail hoch: {thumb_file.name}")

                media = MediaFileUpload(str(thumb_file), mimetype='image/jpeg')

                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=media
                ).execute()

                emit("thumbnail_success")
                print("✓ Thumbnail hochgeladen")

            except HttpError as e:
                emit("thumbnail_error", message=str(e))
                print(f"⚠ Warnung: Thumbnail konnte nicht hochgeladen werden: {e}")
            except Exception as e:
                emit("thumbnail_error", message=str(e))
                print(f"⚠ Warnung: Unerwarteter Fehler bei Thumbnail: {e}")

    # ===========================
    # Erfolgreich abgeschlossen
    # ===========================
    resolved_title = (
        factsheet_data.get('snippet', {}).get('title')
        or factsheet_data.get('title')
        or 'Unbekannter Titel'
    )
    result = UploadResult(
        video_id=video_id,
        title=resolved_title
    )
    try:
        update_source_folder(video_id, str(Path(video_path).parent))
    except Exception:
        pass

    return result


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
