"""
Hilfsfunktionen zum Abruf vorhandener YouTube-Uploads.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional

from googleapiclient.errors import HttpError

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
