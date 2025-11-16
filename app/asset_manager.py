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
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageTk, ImageDraw
from pathlib import Path

from app.youtube_assets import fetch_uploaded_videos, update_video_metadata, upload_video_thumbnail
from app.uploader import UploadError
from app.config import CHANNEL_PUBLIC_URL, CHANNEL_STUDIO_URL
from app.source_map import get_source_folder
from app.svg_icons import load_upload_icon


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
            text="YT-Kanal",
            command=self._open_channel,
            bootstyle=PRIMARY
        ).pack(side=LEFT, padx=5)

        ttk.Button(
            toolbar,
            text="YT-Studio",
            command=self._open_studio,
            bootstyle=PRIMARY
        ).pack(side=LEFT, padx=5)

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

        self.scroll_frame = tk.Frame(self.canvas, bg="#f4f4f4")
        self.scroll_frame.columnconfigure(0, weight=1)

        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

    def _open_channel(self):
        """Öffnet öffentlichen Kanal im Browser."""
        self._open_in_browser(CHANNEL_PUBLIC_URL)

    def _open_studio(self):
        """Öffnet YouTube Studio im Browser."""
        self._open_in_browser(CHANNEL_STUDIO_URL)

    def _load_assets(self):
        """Startet Thread zum Abruf der YouTube-Daten."""
        self.status_label.config(text="Lade Daten...")
        self.thumbnail_cache.clear()
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

        header_frame = tk.Frame(self.scroll_frame, bg="white", padx=8, pady=8)
        header_frame.grid(row=index * 2, column=0, sticky="ew")
        header_frame.columnconfigure(2, weight=1)

        thumb_url = self._get_thumbnail_url(snippet.get("thumbnails"))

        # Container für Thumbnail + Upload-Icon
        thumb_container = tk.Frame(header_frame, bg="white")
        thumb_container.grid(row=0, column=0, rowspan=3, padx=5, pady=5)

        thumb_label = tk.Label(thumb_container, cursor="hand2", bg="white")
        thumb_label.pack()
        self._load_thumbnail_async(thumb_url, thumb_label, video["id"])

        title = snippet.get("title", "Ohne Titel")
        published = snippet.get("publishedAt", "")[:10]
        privacy = status.get("privacyStatus", "n/a")
        views = stats.get("viewCount", "0")

        title_label = tk.Label(
            header_frame,
            text=title,
            font=("Ubuntu", 12, "bold"),
            bg="white"
        )
        title_label.grid(row=0, column=1, columnspan=2, sticky="w", padx=5)

        status_row = tk.Frame(header_frame, bg="white")
        status_row.grid(row=1, column=1, columnspan=2, sticky="w", padx=5, pady=(0, 2))

        tk.Label(
            status_row,
            text=self._format_privacy(privacy),
            font=("Ubuntu", 10, "bold"),
            bg="white"
        ).pack(side=LEFT, padx=(0, 5))

        subs_frame = tk.Frame(status_row, bg="white")
        subs_frame.pack(side=LEFT)
        for label, active in self._get_sub_badges(video):
            tk.Label(
                subs_frame,
                text=f"{'☑' if active else '☐'} {label}",
                bg="white",
                fg="#555555",
                padx=2
            ).pack(side=LEFT, padx=2)

        info_text = f"Veröffentlicht: {published or '–'}    Aufrufe: {views}"
        info_label = tk.Label(header_frame, text=info_text, bg="white", fg="#555555")
        info_label.grid(row=2, column=1, columnspan=2, sticky="w", padx=5, pady=(0, 5))

        def toggle_detail(event=None):
            self._toggle_detail(detail_frame)

        for widget in (title_label, status_row, info_label):
            widget.bind("<Button-1>", toggle_detail)
            widget.configure(cursor="hand2")

        detail_frame = tk.Frame(self.scroll_frame, padx=10, pady=10, bg="white")
        detail_frame.grid(row=index * 2 + 1, column=0, sticky="ew", padx=(30, 0))
        detail_frame.columnconfigure(1, weight=1)

        self._populate_detail(detail_frame, video, thumb_url)
        detail_frame.grid_remove()

        # Horizontale Trennlinie (als Frame für bessere Sichtbarkeit)
        separator_frame = tk.Frame(self.scroll_frame, height=1, bg="#cccccc")
        separator_frame.grid(row=index * 2 + 2, column=0, sticky="ew", pady=(10, 10), padx=15)

    def _populate_detail(self, parent: ttk.Frame, video: Dict[str, Any], thumbnail_url: str):
        """Befüllt Detailabschnitt mit Informationen."""
        snippet = video.get("snippet", {})
        stats = video.get("statistics", {})
        status = video.get("status", {})
        content = video.get("contentDetails", {})

        row = 0
        ttk.Label(parent, text="Titel:", font=("Ubuntu", 10, "bold")).grid(row=row, column=0, sticky="nw", pady=2, padx=5)
        title_var = tk.StringVar(value=snippet.get("title", ""))
        ttk.Entry(parent, textvariable=title_var).grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        row += 1

        ttk.Label(parent, text="Beschreibung:", font=("Ubuntu", 10, "bold")).grid(row=row, column=0, sticky="nw", pady=2, padx=5)
        desc_text = tk.Text(parent, height=5)
        desc_text.insert("1.0", snippet.get("description", ""))
        desc_text.grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        row += 1

        ttk.Label(parent, text="Sichtbarkeit:", font=("Ubuntu", 10, "bold")).grid(row=row, column=0, sticky="nw", pady=2, padx=5)
        privacy_var = tk.StringVar(value=status.get("privacyStatus", "unlisted"))
        ttk.Combobox(parent, textvariable=privacy_var, values=["public", "unlisted", "private"], state="readonly").grid(row=row, column=1, sticky="w", pady=2, padx=5)
        row += 1

        ttk.Label(parent, text="Veröffentlichung (ISO):", font=("Ubuntu", 10, "bold")).grid(row=row, column=0, sticky="nw", pady=2, padx=5)
        publish_var = tk.StringVar(value=status.get("publishAt", ""))
        ttk.Entry(parent, textvariable=publish_var).grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        row += 1

        ttk.Label(parent, text="Tags (Kommagetrennt):", font=("Ubuntu", 10, "bold")).grid(row=row, column=0, sticky="nw", pady=2, padx=5)
        tags_var = tk.StringVar(value=", ".join(snippet.get("tags", [])))
        ttk.Entry(parent, textvariable=tags_var).grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        row += 1

        ttk.Label(parent, text="Upload-ID:", font=("Ubuntu", 10, "bold")).grid(row=row, column=0, sticky="nw", pady=2, padx=5)
        ttk.Label(parent, text=video.get("id")).grid(row=row, column=1, sticky="nw", pady=2, padx=5)
        row += 1

        stats_text = f"Aufrufe: {stats.get('viewCount','0')} • Likes: {stats.get('likeCount','0')} • Kommentare: {stats.get('commentCount','0')}"
        ttk.Label(parent, text=stats_text).grid(row=row, column=1, sticky="w", pady=2, padx=5)
        row += 1

        button_frame = ttk.Frame(parent)
        button_frame.grid(row=row, column=0, columnspan=2, pady=(10, 0), sticky="e")

        studio_url = f"https://studio.youtube.com/video/{video['id']}/edit"
        watch_url = f"https://www.youtube.com/watch?v={video['id']}"

        ttk.Button(
            button_frame,
            text="YouTube öffnen",
            command=lambda url=studio_url: self._open_in_browser(url),
            bootstyle=PRIMARY
        ).pack(side=LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="⧉",
            width=3,
            command=lambda: self._copy_to_clipboard(watch_url),
            bootstyle=SECONDARY
        ).pack(side=LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="Änderungen speichern",
            command=lambda: self._save_metadata(
                video_id=video.get("id"),
                title=title_var.get(),
                description=desc_text.get("1.0", "end").strip(),
                privacy=privacy_var.get(),
                publish_at=publish_var.get().strip(),
                tags=tags_var.get()
            ),
            bootstyle=SUCCESS
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

    def _load_thumbnail_async(self, url: str, label: tk.Label, video_id: str):
        """Lädt Thumbnail-Bild in separatem Thread und fügt Upload-Icon hinzu."""
        if not url:
            label.config(text="[kein Bild]")
            return

        cache_key = f"{url}_with_icon"
        if cache_key in self.thumbnail_cache:
            label.config(image=self.thumbnail_cache[cache_key])
            label.image = self.thumbnail_cache[cache_key]
            label.bind("<Button-1>", lambda e: self._upload_thumbnail(video_id))
            return

        def worker():
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                img = Image.open(BytesIO(response.content))
                img.thumbnail((160, 90), Image.Resampling.LANCZOS)

                # Upload-Icon unten rechts einzeichnen
                img_with_icon = self._add_upload_icon(img)

                photo = ImageTk.PhotoImage(img_with_icon)
                self.thumbnail_cache[cache_key] = photo
                self.after(0, lambda: self._apply_thumbnail(label, cache_key, video_id))
            except Exception:
                self.after(0, lambda: label.config(text="[Thumb Fehler]"))

        threading.Thread(target=worker, daemon=True).start()

    def _add_upload_icon(self, img: Image.Image) -> Image.Image:
        """Fügt Upload-Icon aus SVG unten rechts im Thumbnail ein."""
        # Erstelle eine Kopie
        img = img.copy()

        # Lade Upload-Icon (weiß auf orange)
        icon_size = 28
        upload_icon = load_upload_icon(size=icon_size, bg_color='#ff7b33')

        # Icon-Position: unten rechts
        padding = 4
        x = img.width - icon_size - padding
        y = img.height - icon_size - padding

        # Konvertiere Basis-Bild zu RGBA falls nötig
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        # Füge Upload-Icon hinzu
        if upload_icon.mode == 'RGBA':
            img.paste(upload_icon, (x, y), upload_icon)
        else:
            img.paste(upload_icon, (x, y))

        # Zurück zu RGB konvertieren
        if img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background

        return img

    def _apply_thumbnail(self, label: tk.Label, cache_key: str, video_id: str):
        """Setzt zwischengespeichertes Thumbnail auf Label."""
        photo = self.thumbnail_cache.get(cache_key)
        if photo:
            label.config(image=photo)
            label.image = photo
            label.bind("<Button-1>", lambda e: self._upload_thumbnail(video_id))

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

    def _format_privacy(self, privacy: str) -> str:
        mapping = {
            "public": "Öffentlich",
            "unlisted": "Nicht gelistet",
            "private": "Privat"
        }
        return mapping.get(privacy, privacy or "–")

    def _get_sub_badges(self, video: Dict[str, Any]):
        caption_flag = video.get("contentDetails", {}).get("caption")
        soft = caption_flag == "true"
        hard = False  # keine verlässliche API-Angabe
        none = not soft and not hard
        return [
            ("Soft Subs", soft),
            ("Hard Subs", hard),
            ("No Subs", none)
        ]

    def _get_thumbnail_url(self, thumbnails: Dict[str, Any]) -> str:
        """Wählt bestes Thumbnail aus Snippet."""
        if not thumbnails:
            return ""
        for key in ("maxres", "standard", "high", "medium", "default"):
            data = thumbnails.get(key)
            if data and data.get("url"):
                return data["url"]
        return ""

    def _download_thumbnail(self, url: str, video_id: str):
        """Speichert YouTube-Thumbnail lokal."""
        if not url:
            messagebox.showerror("Kein Thumbnail", "Für dieses Video ist kein Thumbnail verfügbar.")
            return

        filename = f"{video_id}_thumbnail.jpg"
        save_path = filedialog.asksaveasfilename(
            title="Thumbnail speichern",
            initialfile=filename,
            defaultextension=".jpg",
            filetypes=[("JPEG", "*.jpg"), ("Alle Dateien", "*.*")]
        )
        if not save_path:
            return

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            with open(save_path, "wb") as outfile:
                outfile.write(response.content)
            self.status_label.config(text=f"Thumbnail gespeichert: {Path(save_path).name}")
        except Exception as e:
            messagebox.showerror("Fehler", f"Thumbnail konnte nicht gespeichert werden:\n{e}")

    def _upload_thumbnail(self, video_id: str):
        """Lädt ein manuell ausgewähltes Thumbnail zu YouTube hoch."""
        if not video_id:
            return

        initial_dir = get_source_folder(video_id) or str(Path.home())
        file_path = filedialog.askopenfilename(
            title="Thumbnail auswählen",
            filetypes=[
                ("Bilddateien", "*.jpg *.jpeg *.png"),
                ("Alle Dateien", "*.*")
            ],
            initialdir=initial_dir
        )
        if not file_path:
            return

        self.status_label.config(text="Thumbnail-Upload gestartet...")
        self.thumbnail_cache.clear()
        try:
            upload_video_thumbnail(video_id, file_path)
            self.status_label.config(text="Thumbnail aktualisiert – Aktualisiere Liste...")
            self._load_assets()
        except UploadError as e:
            messagebox.showerror("YouTube-Fehler", str(e))
        except Exception as e:
            messagebox.showerror("Fehler", str(e))

    def _save_metadata(self, video_id: str, title: str, description: str, privacy: str, publish_at: str, tags: str):
        """Speichert geänderte Metadaten via YouTube API."""
        if not video_id:
            return

        tags_list = [t.strip() for t in tags.split(",") if t.strip()]
        publish_value = publish_at or None
        try:
            update_video_metadata(
                video_id=video_id,
                title=title.strip(),
                description=description,
                privacy_status=privacy,
                tags=tags_list,
                publish_at=publish_value
            )
            self.status_label.config(text="Änderungen gespeichert")
            self._load_assets()
        except UploadError as e:
            messagebox.showerror("YouTube-Fehler", str(e))
        except Exception as e:
            messagebox.showerror("Fehler", str(e))
