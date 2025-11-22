"""
Hilfsfunktionen zum Abruf vorhandener YouTube-Uploads.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from pathlib import Path

from app.auth import create_youtube_client, AuthError
from app.config import CLIENT_SECRETS_PATH, TOKEN_PATH
from app.uploader import UploadError


def fetch_uploaded_videos(max_results: int = 25) -> List[Dict[str, Any]]:
    """
    Ruft die zuletzt hochgeladenen Videos des authentifizierten Kanals ab.

    Args:
        max_results: Anzahl der zurückzugebenden Videos (max. 50 pro API-Call)

    Returns:
        Liste von Dicts mit Snippet-, Status- und Statistikdaten
    """
    try:
        youtube = create_youtube_client(CLIENT_SECRETS_PATH, TOKEN_PATH)
    except AuthError as e:
        raise UploadError(f"Authentifizierung fehlgeschlagen:\n{e}")

    try:
        channels_response = youtube.channels().list(
            part="contentDetails",
            mine=True
        ).execute()

        items = channels_response.get("items", [])
        if not items:
            return []

        uploads_playlist = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

        playlist_items = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=uploads_playlist,
            maxResults=min(max_results, 50)
        ).execute()

        video_ids = [
            entry["contentDetails"]["videoId"]
            for entry in playlist_items.get("items", [])
        ]

        if not video_ids:
            return []

        videos_response = youtube.videos().list(
            part="snippet,statistics,status,contentDetails",
            id=",".join(video_ids)
        ).execute()

        videos = videos_response.get("items", [])
        # Re-sort to match playlist order
        id_order = {vid_id: idx for idx, vid_id in enumerate(video_ids)}
        videos.sort(key=lambda v: id_order.get(v["id"], 0))

        return videos

    except HttpError as e:
        raise UploadError(f"YouTube API-Fehler beim Laden der Videos:\n{e}")


def update_video_metadata(
    video_id: str,
    title: str,
    description: str,
    privacy_status: str,
    tags: List[str],
    publish_at: Optional[str] = None
) -> Dict[str, Any]:
    """
    Aktualisiert Metadaten eines bestehenden YouTube-Videos.
    """
    try:
        youtube = create_youtube_client(CLIENT_SECRETS_PATH, TOKEN_PATH)
    except AuthError as e:
        raise UploadError(f"Authentifizierung fehlgeschlagen:\n{e}")

    body: Dict[str, Any] = {
        "id": video_id,
        "snippet": {
            "title": title or "Untitled",
            "description": description or "",
            "categoryId": "22",
        },
        "status": {
            "privacyStatus": privacy_status or "unlisted"
        }
    }

    if tags:
        body["snippet"]["tags"] = tags

    if publish_at:
        body["status"]["publishAt"] = publish_at

    try:
        response = youtube.videos().update(
            part="snippet,status",
            body=body
        ).execute()
        return response
    except HttpError as e:
        raise UploadError(f"YouTube API-Fehler beim Aktualisieren:\n{e}")


def update_video_status_flags(
    video_id: str,
    made_for_kids: bool,
    embeddable: bool
) -> Dict[str, Any]:
    """
    Aktualisiert ForKids und Embeddable Flags eines YouTube-Videos.

    Args:
        video_id: YouTube Video-ID
        made_for_kids: True wenn Video speziell für Kinder
        embeddable: True wenn Video eingebettet werden darf

    Returns:
        API-Response mit aktualisierten Video-Informationen
    """
    try:
        youtube = create_youtube_client(CLIENT_SECRETS_PATH, TOKEN_PATH)
    except AuthError as e:
        raise UploadError(f"Authentifizierung fehlgeschlagen:\n{e}")

    body: Dict[str, Any] = {
        "id": video_id,
        "status": {
            "selfDeclaredMadeForKids": made_for_kids,
            "embeddable": embeddable
        }
    }

    try:
        response = youtube.videos().update(
            part="status",
            body=body
        ).execute()
        return response
    except HttpError as e:
        raise UploadError(f"YouTube API-Fehler beim Aktualisieren:\n{e}")


def upload_video_thumbnail(video_id: str, thumbnail_path: str) -> Dict[str, Any]:
    """
    Lädt ein benutzerdefiniertes Thumbnail für ein bestehendes Video hoch.
    """
    try:
        youtube = create_youtube_client(CLIENT_SECRETS_PATH, TOKEN_PATH)
    except AuthError as e:
        raise UploadError(f"Authentifizierung fehlgeschlagen:\n{e}")

    media = MediaFileUpload(thumbnail_path, mimetype="image/jpeg")

    try:
        response = youtube.thumbnails().set(
            videoId=video_id,
            media_body=media
        ).execute()
        return response
    except HttpError as e:
        raise UploadError(f"YouTube API-Fehler beim Thumbnail-Upload:\n{e}")


def replace_video_file(video_id: str, video_path: str, progress_callback=None) -> Dict[str, Any]:
    """
    Ersetzt die Video-Datei eines bestehenden YouTube-Videos.
    Behält alle Metadaten (Titel, Beschreibung, URL) bei.

    Args:
        video_id: YouTube Video-ID
        video_path: Pfad zur neuen Video-Datei
        progress_callback: Optional callback(current, total) für Upload-Fortschritt

    Returns:
        API-Response mit aktualisierten Video-Informationen
    """
    try:
        youtube = create_youtube_client(CLIENT_SECRETS_PATH, TOKEN_PATH)
    except AuthError as e:
        raise UploadError(f"Authentifizierung fehlgeschlagen:\n{e}")

    # Erstelle MediaFileUpload mit resumable upload
    media = MediaFileUpload(
        video_path,
        mimetype="video/*",
        resumable=True,
        chunksize=1024 * 1024  # 1MB chunks
    )

    try:
        # Update-Request mit media_body ersetzt das Video
        request = youtube.videos().update(
            part="id,status",
            body={"id": video_id, "status": {}},
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status and progress_callback:
                progress_callback(status.resumable_progress, status.total_size)

        return response

    except HttpError as e:
        raise UploadError(f"YouTube API-Fehler beim Video-Ersatz:\n{e}")


def delete_video(video_id: str) -> None:
    """
    Löscht ein YouTube-Video permanent.

    Args:
        video_id: YouTube Video-ID

    Raises:
        UploadError: Bei Authentifizierungs- oder API-Fehlern
    """
    try:
        youtube = create_youtube_client(CLIENT_SECRETS_PATH, TOKEN_PATH)
    except AuthError as e:
        raise UploadError(f"Authentifizierung fehlgeschlagen:\n{e}")

    try:
        youtube.videos().delete(id=video_id).execute()
    except HttpError as e:
        raise UploadError(f"YouTube API-Fehler beim Löschen:\n{e}")


def find_video_by_title(title: str, max_results: int = 50) -> Optional[Dict[str, Any]]:
    """
    Sucht ein Video anhand des exakten Titels.

    Args:
        title: Exakter Video-Titel
        max_results: Maximale Anzahl Videos zum Durchsuchen

    Returns:
        Video-Dict falls gefunden, sonst None
    """
    try:
        youtube = create_youtube_client(CLIENT_SECRETS_PATH, TOKEN_PATH)
    except AuthError as e:
        raise UploadError(f"Authentifizierung fehlgeschlagen:\n{e}")

    try:
        # Hole alle eigenen Videos
        videos = fetch_uploaded_videos(max_results=max_results)

        # Suche nach exaktem Titel-Match
        for video in videos:
            video_title = video.get("snippet", {}).get("title", "")
            if video_title == title:
                return video

        return None

    except Exception as e:
        raise UploadError(f"Fehler beim Suchen des Videos:\n{e}")
