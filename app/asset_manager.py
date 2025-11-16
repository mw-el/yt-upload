"""
GUI-Fenster zur Verwaltung bereits hochgeladener YouTube-Assets.
"""

from __future__ import annotations

import threading
import os
import webbrowser
from io import BytesIO
from typing import List, Dict, Any

import requests
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageTk

from app.youtube_assets import fetch_uploaded_videos
from app.uploader import UploadError


class AssetManagerWindow(tk.Toplevel):
    """Separates Fenster zur Anzeige bereits hochgeladener Videos."""

    def __init__(self, owner):
        parent = getattr(owner, "root", owner)
        super().__init__(parent)
        self.owner = owner
        self.title("YouTube Asset-Manager")
        self.geometry("1100x700")
        self.minsize(900, 600)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.thumbnail_cache: Dict[str, ImageTk.PhotoImage] = {}
        self.accordion_items: List[Dict[str, Any]] = []

        self._build_ui()
        self._load_assets()

    def _build_ui(self):
        """Erstellt Grundlayout."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(self, padding=(15, 10))
        toolbar.grid(row=0, column=0, sticky="ew")

        ttk.Label(
            toolbar,
            text="Uploads auf YouTube",
            font=("Ubuntu", 16, "bold")
        ).pack(side=LEFT)

        ttk.Button(
            toolbar,
            text="Aktualisieren",
            bootstyle=PRIMARY,
            command=self._load_assets
        ).pack(side=LEFT, padx=10)

        ttk.Button(
            toolbar,
            text="Im Browser öffnen",
            command=self._open_studio,
            bootstyle=SECONDARY
        ).pack(side=LEFT)

        self.status_label = ttk.Label(toolbar, text="", padding=5, foreground="gray")
        self.status_label.pack(side=RIGHT)

        # Scrollbereich
        container = ttk.Frame(self, padding=10)
        container.grid(row=1, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(container, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(container, orient=VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scroll_frame = ttk.Frame(self.canvas)
        self.scroll_frame.columnconfigure(0, weight=1)

        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

    def _open_studio(self):
        """Öffnet YouTube Studio im Browser."""
        self._open_in_browser("https://studio.youtube.com/")

    def _load_assets(self):
        """Startet Thread zum Abruf der YouTube-Daten."""
        self.status_label.config(text="Lade Daten...")
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        threading.Thread(target=self._load_assets_worker, daemon=True).start()

    def _load_assets_worker(self):
        try:
            videos = fetch_uploaded_videos(max_results=25)
            self.after(0, lambda: self._render_assets(videos))
            self.after(0, lambda: self.status_label.config(text=f"{len(videos)} Videos geladen"))
        except UploadError as e:
            self.after(0, lambda: self.status_label.config(text=f"Fehler: {e}"))
        except Exception as e:
            self.after(0, lambda: self.status_label.config(text=f"Fehler: {e}"))

    def _render_assets(self, videos: List[Dict[str, Any]]):
        """Erstellt Accordion-Einträge für jedes Video."""
        for idx, video in enumerate(videos):
            self._create_accordion_item(idx, video)

    def _create_accordion_item(self, index: int, video: Dict[str, Any]):
        """Erzeugt Entry mit Header + Detailansicht."""
        snippet = video.get("snippet", {})
        stats = video.get("statistics", {})
        status = video.get("status", {})

        header_frame = ttk.Frame(self.scroll_frame, bootstyle="info")
        header_frame.grid(row=index * 2, column=0, sticky="ew", pady=(0, 2))
        header_frame.columnconfigure(2, weight=1)

        thumb_label = ttk.Label(header_frame)
        thumb_label.grid(row=0, column=0, rowspan=2, padx=5, pady=5)
        self._load_thumbnail_async(snippet.get("thumbnails"), thumb_label)

        title = snippet.get("title", "Ohne Titel")
        published = snippet.get("publishedAt", "")[:10]
        privacy = status.get("privacyStatus", "n/a")
        views = stats.get("viewCount", "0")

        ttk.Label(
            header_frame,
            text=title,
            font=("Ubuntu", 12, "bold")
        ).grid(row=0, column=1, columnspan=2, sticky="w", padx=5)

        meta_text = f"Veröffentlicht: {published} • Sichtbarkeit: {privacy} • Aufrufe: {views}"
        ttk.Label(header_frame, text=meta_text).grid(row=1, column=1, sticky="w", padx=5)

        toggle_btn = ttk.Button(
            header_frame,
            text="Details",
            command=lambda: self._toggle_detail(detail_frame),
            bootstyle=SECONDARY
        )
        toggle_btn.grid(row=0, column=3, rowspan=2, padx=5, pady=5)

        detail_frame = ttk.Frame(self.scroll_frame, padding=10, bootstyle="secondary")
        detail_frame.grid(row=index * 2 + 1, column=0, sticky="ew", padx=(30, 0), pady=(0, 10))
        detail_frame.columnconfigure(1, weight=1)

        self._populate_detail(detail_frame, video)
        detail_frame.grid_remove()

    def _populate_detail(self, parent: ttk.Frame, video: Dict[str, Any]):
        """Befüllt Detailabschnitt mit Informationen."""
        snippet = video.get("snippet", {})
        stats = video.get("statistics", {})
        status = video.get("status", {})
        content = video.get("contentDetails", {})

        fields = [
            ("Titel", snippet.get("title", "—")),
            ("Beschreibung", snippet.get("description", "—")),
            ("Upload-ID", video.get("id")),
            ("Status", status.get("uploadStatus", "—")),
            ("Sichtbarkeit", status.get("privacyStatus", "—")),
            ("Geplante Veröffentlichung", status.get("publishAt", "—")),
            ("Dauer", content.get("duration", "—")),
            ("Aufrufe", stats.get("viewCount", "0")),
            ("Likes", stats.get("likeCount", "0")),
            ("Kommentare", stats.get("commentCount", "0"))
        ]

        row = 0
        for label, value in fields:
            ttk.Label(parent, text=f"{label}:", font=("Ubuntu", 10, "bold")).grid(row=row, column=0, sticky="nw", pady=2, padx=5)
            ttk.Label(parent, text=str(value)).grid(row=row, column=1, sticky="nw", pady=2, padx=5)
            row += 1

        button_frame = ttk.Frame(parent)
        button_frame.grid(row=row, column=0, columnspan=2, pady=(10, 0))

        ttk.Button(
            button_frame,
            text="YouTube öffnen",
            command=lambda vid=video: self._open_in_browser(f"https://www.youtube.com/watch?v={vid['id']}"),
            bootstyle=PRIMARY
        ).pack(side=LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="Link kopieren",
            command=lambda vid=video: self._copy_to_clipboard(f"https://www.youtube.com/watch?v={vid['id']}"),
            bootstyle=SECONDARY
        ).pack(side=LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="Noch nicht implementiert: Löschen",
            state=DISABLED
        ).pack(side=LEFT, padx=5)

    def _copy_to_clipboard(self, text: str):
        """Kopiert Text in Zwischenablage."""
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status_label.config(text="Link kopiert.")

    def _toggle_detail(self, frame: ttk.Frame):
        """Zeigt/verbirgt Detail-Frame."""
        if frame.winfo_ismapped():
            frame.grid_remove()
        else:
            frame.grid()

    def _load_thumbnail_async(self, thumbnails: Dict[str, Any], label: ttk.Label):
        """Lädt Thumbnail-Bild in separatem Thread."""
        url = None
        if thumbnails:
            url = thumbnails.get("medium", thumbnails.get("default", {})).get("url")
        if not url:
            label.config(text="[kein Bild]")
            return

        if url in self.thumbnail_cache:
            label.config(image=self.thumbnail_cache[url])
            label.image = self.thumbnail_cache[url]
            return

        def worker():
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                img = Image.open(BytesIO(response.content))
                img.thumbnail((160, 90), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.thumbnail_cache[url] = photo
                self.after(0, lambda: self._apply_thumbnail(label, url))
            except Exception:
                self.after(0, lambda: label.config(text="[Thumb Fehler]"))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_thumbnail(self, label: ttk.Label, url: str):
        """Setzt zwischengespeichertes Thumbnail auf Label."""
        photo = self.thumbnail_cache.get(url)
        if photo:
            label.config(image=photo)
            label.image = photo

    def _open_in_browser(self, url: str):
        """Öffnet URL bevorzugt in Firefox."""
        browser_choice = os.getenv("YOUTUBE_OAUTH_BROWSER", os.getenv("BROWSER"))
        opened = False
        if browser_choice:
            try:
                browser = webbrowser.get(browser_choice)
                browser.open(url)
                opened = True
            except webbrowser.Error:
                opened = False
        if not opened:
            webbrowser.open(url)

    def _on_close(self):
        """Stellt sicher, dass Owner-Referenz zurückgesetzt wird."""
        if hasattr(self.owner, "asset_window"):
            self.owner.asset_window = None
        self.destroy()
