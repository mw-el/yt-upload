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

from app.youtube_assets import fetch_uploaded_videos, update_video_metadata, upload_video_thumbnail, replace_video_file, delete_video
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
        self.geometry("780x750")
        self.minsize(700, 550)
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

        ttk.Button(
            toolbar,
            text="MD Export",
            command=self._export_markdown,
            bootstyle=SECONDARY
        ).pack(side=LEFT, padx=10)

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

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")

        # Scrollregion und Canvas-Breite synchronisieren
        self.scroll_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

    def _on_frame_configure(self, event=None):
        """Aktualisiert Scrollregion wenn sich Frame-Inhalt ändert."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        """Passt scroll_frame-Breite an Canvas-Breite an."""
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _open_channel(self):
        """Öffnet öffentlichen Kanal im Browser."""
        self._open_in_browser(CHANNEL_PUBLIC_URL)

    def _open_studio(self):
        """Öffnet YouTube Studio im Browser."""
        self._open_in_browser(CHANNEL_STUDIO_URL)

    def _export_markdown(self):
        """Exportiert Markdown-Tabelle mit Videotiteln und Unlisted-IDs."""
        self.status_label.config(text="Lade Videos für Export...")

        def worker():
            try:
                videos = fetch_uploaded_videos(max_results=50)
                self.after(0, lambda: self._generate_markdown_file(videos))
            except Exception as e:
                self.after(0, lambda: self.status_label.config(text=f"Fehler: {e}"))

        threading.Thread(target=worker, daemon=True).start()

    def _generate_markdown_file(self, videos):
        """Generiert Markdown-Datei mit Titel/Unlisted-ID Tabelle."""
        if not videos:
            self.status_label.config(text="Keine Videos zum Exportieren")
            return

        # Gruppiere Videos nach Titel
        groups = self._group_videos_by_title(videos)

        # Sammle Titel und Unlisted-IDs
        entries = []
        for group_title, group_videos in groups.items():
            # Finde unlisted Video (neutral_embed)
            unlisted_video = next(
                (v for v in group_videos if v.get("status", {}).get("privacyStatus") == "unlisted"),
                None
            )

            if unlisted_video:
                title = unlisted_video.get("snippet", {}).get("title", "Ohne Titel")
                video_id = unlisted_video.get("id", "")
                entries.append((title, video_id))
            elif len(group_videos) == 1:
                # Einzelvideo ohne Gruppierung
                video = group_videos[0]
                title = video.get("snippet", {}).get("title", "Ohne Titel")
                video_id = video.get("id", "")
                privacy = video.get("status", {}).get("privacyStatus", "")
                if privacy == "unlisted":
                    entries.append((title, video_id))

        if not entries:
            self.status_label.config(text="Keine unlisted Videos gefunden")
            return

        # Markdown generieren
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d")

        md_content = f"# YouTube Unlisted Videos\n\n"
        md_content += f"Exportiert am: {date_str}\n\n"
        md_content += "| Titel | Video-ID |\n"
        md_content += "|-------|----------|\n"

        for title, video_id in entries:
            # Escape pipe-Zeichen in Titeln
            safe_title = title.replace("|", "\\|")
            md_content += f"| {safe_title} | {video_id} |\n"

        # Datei speichern
        save_path = filedialog.asksaveasfilename(
            title="Markdown-Export speichern",
            initialfile=f"youtube_unlisted_{date_str}.md",
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("Alle Dateien", "*.*")]
        )

        if not save_path:
            self.status_label.config(text="Export abgebrochen")
            return

        try:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(md_content)
            self.status_label.config(text=f"Exportiert: {len(entries)} Videos → {Path(save_path).name}")
        except Exception as e:
            messagebox.showerror("Fehler", f"Export fehlgeschlagen:\n{e}")
            self.status_label.config(text="Export fehlgeschlagen")

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
        """Erstellt Accordion-Einträge für jedes Video oder gruppiert nach Titel."""
        # Gruppiere Videos nach Titel-Anfang
        groups = self._group_videos_by_title(videos)

        idx = 0
        for group_title, group_videos in groups.items():
            if len(group_videos) == 1:
                # Einzelnes Video → normale Darstellung
                self._create_accordion_item(idx, group_videos[0])
            else:
                # Mehrere Videos → gruppierte Darstellung
                self._create_grouped_accordion_item(idx, group_title, group_videos)
            idx += 1

    def _group_videos_by_title(self, videos: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Gruppiert Videos nach Titel-Anfang (erste ~50 Zeichen)."""
        groups: Dict[str, List[Dict[str, Any]]] = {}

        for video in videos:
            title = video.get("snippet", {}).get("title", "")
            # Verwende erste 50 Zeichen als Gruppen-Schlüssel
            prefix = title[:50].strip()

            if prefix not in groups:
                groups[prefix] = []
            groups[prefix].append(video)

        return groups

    def _detect_profile(self, video: Dict[str, Any]) -> str:
        """Erkennt Profil basierend auf Privacy Status."""
        privacy = video.get("status", {}).get("privacyStatus", "")

        # Mapping: unlisted = neutral_embed, public = public_youtube, private = social_subtitled
        if privacy == "unlisted":
            return "neutral_embed"
        elif privacy == "public":
            return "public_youtube"
        elif privacy == "private":
            return "social_subtitled"
        else:
            return "unknown"

    def _create_grouped_accordion_item(self, index: int, group_title: str, videos: List[Dict[str, Any]]):
        """Erzeugt gruppierten Entry für Multi-Profil-Videos."""
        # Sortiere Videos nach Profil-Priorität: neutral_embed, public_youtube, social_subtitled
        profile_order = {"neutral_embed": 0, "public_youtube": 1, "social_subtitled": 2, "unknown": 3}
        sorted_videos = sorted(videos, key=lambda v: profile_order.get(self._detect_profile(v), 99))

        # Hauptvideo (neutral_embed, falls vorhanden)
        main_video = sorted_videos[0]
        snippet = main_video.get("snippet", {})
        stats = main_video.get("statistics", {})
        status = main_video.get("status", {})

        header_frame = tk.Frame(self.scroll_frame, bg="white", padx=8, pady=8)
        header_frame.grid(row=index * 2, column=0, sticky="ew")
        header_frame.columnconfigure(2, weight=1)

        thumb_url = self._get_thumbnail_url(snippet.get("thumbnails"))

        # Container für Thumbnail + Buttons (Link + Upload)
        thumb_container = tk.Frame(header_frame, bg="white")
        thumb_container.grid(row=0, column=0, rowspan=3, padx=5, pady=5)

        thumb_label = tk.Label(thumb_container, cursor="hand2", bg="white")
        thumb_label.pack()
        # Bei gruppierten Videos: Alle Video-IDs für Thumbnail-Upload sammeln
        all_video_ids = [v["id"] for v in sorted_videos]
        self._load_thumbnail_async(thumb_url, thumb_label, all_video_ids, add_link_button=True)

        title = snippet.get("title", "Ohne Titel")
        published = snippet.get("publishedAt", "")[:10]

        # Finde unlisted Video-ID für Anzeige neben Titel
        unlisted_video = next((v for v in sorted_videos if self._detect_profile(v) == "neutral_embed"), None)
        unlisted_id = unlisted_video["id"] if unlisted_video else sorted_videos[0]["id"]

        # Zeige alle Profile als Status mit IDs
        profiles_with_ids = " | ".join([f"{self._detect_profile(v)}:{v['id']}" for v in sorted_videos])

        # Titel-Zeile mit Unlisted Video-ID
        title_row = tk.Frame(header_frame, bg="white")
        title_row.grid(row=0, column=1, columnspan=2, sticky="w", padx=5)

        title_label = tk.Label(
            title_row,
            text=title,
            font=("Ubuntu", 12, "bold"),
            bg="white"
        )
        title_label.pack(side=LEFT)

        # Unlisted Video-ID neben Titel (grau, kleiner)
        tk.Label(
            title_row,
            text=f"  [{unlisted_id}]",
            font=("Ubuntu", 9),
            bg="white",
            fg="#888888"
        ).pack(side=LEFT)

        status_row = tk.Frame(header_frame, bg="white")
        status_row.grid(row=1, column=1, columnspan=2, sticky="w", padx=5, pady=(0, 2))

        tk.Label(
            status_row,
            text=f"🔗 Gruppe ({len(videos)} Videos): {profiles_with_ids}",
            font=("Ubuntu", 9),
            bg="white",
            fg="#555555"
        ).pack(side=LEFT, padx=(0, 5))

        # ForKids und Embeddable Checkboxen für alle Videos in der Gruppe
        main_status = main_video.get("status", {})
        made_for_kids = main_status.get("madeForKids", False)
        embeddable = main_status.get("embeddable", True)

        kids_var = tk.BooleanVar(value=made_for_kids)
        embed_var = tk.BooleanVar(value=embeddable)

        ttk.Checkbutton(
            status_row,
            text="ForKids",
            variable=kids_var,
            command=lambda: self._update_grouped_video_flags(sorted_videos, kids_var.get(), embed_var.get()),
            bootstyle="round-toggle"
        ).pack(side=LEFT, padx=(10, 2))

        ttk.Checkbutton(
            status_row,
            text="Embeddable",
            variable=embed_var,
            command=lambda: self._update_grouped_video_flags(sorted_videos, kids_var.get(), embed_var.get()),
            bootstyle="round-toggle"
        ).pack(side=LEFT, padx=2)

        # Aggregierte Stats (vom Hauptvideo) + Löschen-Button
        info_row = tk.Frame(header_frame, bg="white")
        info_row.grid(row=2, column=1, columnspan=2, sticky="ew", padx=5, pady=(0, 5))

        views = stats.get("viewCount", "0")
        info_text = f"Veröffentlicht: {published or '–'}    Aufrufe: {views}"
        info_label = tk.Label(info_row, text=info_text, bg="white", fg="#555555")
        info_label.pack(side=LEFT)

        # Löschen-Button für alle Videos der Gruppe
        delete_btn = ttk.Button(
            info_row,
            text="🗑",
            command=lambda: self._delete_grouped_videos(sorted_videos, title),
            bootstyle="danger-outline",
            width=3
        )
        delete_btn.pack(side=RIGHT, padx=5)

        def toggle_detail(event=None):
            self._toggle_detail(detail_frame)

        for widget in (title_row, title_label, status_row, info_label):
            widget.bind("<Button-1>", toggle_detail)
            widget.configure(cursor="hand2")

        # Detail-Frame für alle Videos
        detail_frame = tk.Frame(self.scroll_frame, padx=10, pady=10, bg="white")
        detail_frame.grid(row=index * 2 + 1, column=0, sticky="ew", padx=(30, 0))
        detail_frame.columnconfigure(1, weight=1)

        self._populate_grouped_detail(detail_frame, sorted_videos)
        detail_frame.grid_remove()

        # Schwarze Trennlinie
        separator_frame = tk.Frame(self.scroll_frame, height=2, bg="#000000")
        separator_frame.grid(row=index * 2 + 2, column=0, sticky="ew", pady=(10, 10), padx=15)

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
        self._load_thumbnail_async(thumb_url, thumb_label, video["id"], add_link_button=False)

        title = snippet.get("title", "Ohne Titel")
        video_id = video.get("id", "")
        published = snippet.get("publishedAt", "")[:10]
        privacy = status.get("privacyStatus", "n/a")
        views = stats.get("viewCount", "0")

        # Titel-Zeile mit Video-ID
        title_row = tk.Frame(header_frame, bg="white")
        title_row.grid(row=0, column=1, columnspan=2, sticky="w", padx=5)

        title_label = tk.Label(
            title_row,
            text=title,
            font=("Ubuntu", 12, "bold"),
            bg="white"
        )
        title_label.pack(side=LEFT)

        # Video-ID neben Titel (grau, kleiner)
        tk.Label(
            title_row,
            text=f"  [{video_id}]",
            font=("Ubuntu", 9),
            bg="white",
            fg="#888888"
        ).pack(side=LEFT)

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

        # ForKids und Embeddable Checkboxen im Header
        made_for_kids = status.get("madeForKids", False)
        embeddable = status.get("embeddable", True)

        kids_var = tk.BooleanVar(value=made_for_kids)
        embed_var = tk.BooleanVar(value=embeddable)

        ttk.Checkbutton(
            subs_frame,
            text="ForKids",
            variable=kids_var,
            command=lambda: self._update_video_flags(video["id"], kids_var.get(), embed_var.get()),
            bootstyle="round-toggle"
        ).pack(side=LEFT, padx=(10, 2))

        ttk.Checkbutton(
            subs_frame,
            text="Embeddable",
            variable=embed_var,
            command=lambda: self._update_video_flags(video["id"], kids_var.get(), embed_var.get()),
            bootstyle="round-toggle"
        ).pack(side=LEFT, padx=2)

        # Info-Zeile mit Löschen-Button
        info_row = tk.Frame(header_frame, bg="white")
        info_row.grid(row=2, column=1, columnspan=2, sticky="ew", padx=5, pady=(0, 5))

        info_text = f"Veröffentlicht: {published or '–'}    Aufrufe: {views}"
        info_label = tk.Label(info_row, text=info_text, bg="white", fg="#555555")
        info_label.pack(side=LEFT)

        # Löschen-Button
        delete_btn = ttk.Button(
            info_row,
            text="🗑",
            command=lambda: self._delete_video(video["id"], title),
            bootstyle="danger-outline",
            width=3
        )
        delete_btn.pack(side=RIGHT, padx=5)

        def toggle_detail(event=None):
            self._toggle_detail(detail_frame)

        for widget in (title_row, title_label, status_row, info_label):
            widget.bind("<Button-1>", toggle_detail)
            widget.configure(cursor="hand2")

        detail_frame = tk.Frame(self.scroll_frame, padx=10, pady=10, bg="white")
        detail_frame.grid(row=index * 2 + 1, column=0, sticky="ew", padx=(30, 0))
        detail_frame.columnconfigure(1, weight=1)

        self._populate_detail(detail_frame, video, thumb_url)
        detail_frame.grid_remove()

        # Schwarze Trennlinie
        separator_frame = tk.Frame(self.scroll_frame, height=2, bg="#000000")
        separator_frame.grid(row=index * 2 + 2, column=0, sticky="ew", pady=(10, 10), padx=15)

    def _populate_grouped_detail(self, parent: ttk.Frame, videos: List[Dict[str, Any]]):
        """Befüllt Detailabschnitt für gruppierte Videos."""
        # Verwende Hauptvideo (erstes in sortierter Liste) für gemeinsame Metadaten
        main_video = videos[0]
        snippet = main_video.get("snippet", {})
        stats = main_video.get("statistics", {})

        # Gemeinsame Metadaten (für alle Videos gleich)
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

        ttk.Label(parent, text="Tags (Kommagetrennt):", font=("Ubuntu", 10, "bold")).grid(row=row, column=0, sticky="nw", pady=2, padx=5)
        tags_var = tk.StringVar(value=", ".join(snippet.get("tags", [])))
        ttk.Entry(parent, textvariable=tags_var).grid(row=row, column=1, sticky="ew", pady=2, padx=5)
        row += 1

        # Aggregierte Statistiken
        stats_text = f"Aufrufe: {stats.get('viewCount','0')} • Likes: {stats.get('likeCount','0')} • Kommentare: {stats.get('commentCount','0')}"
        ttk.Label(parent, text=stats_text).grid(row=row, column=1, sticky="w", pady=2, padx=5)
        row += 1

        # Button zum Speichern gemeinsamer Metadaten (aktualisiert alle Videos in der Gruppe)
        save_button_frame = ttk.Frame(parent)
        save_button_frame.grid(row=row, column=0, columnspan=2, pady=(10, 15), sticky="e")

        ttk.Button(
            save_button_frame,
            text="Gemeinsame Metadaten für alle speichern",
            command=lambda: self._save_grouped_metadata(
                videos=videos,
                title=title_var.get(),
                description=desc_text.get("1.0", "end").strip(),
                tags=tags_var.get()
            ),
            bootstyle=SUCCESS
        ).pack(side=LEFT, padx=5)
        row += 1

        # Trennlinie vor Video-Varianten
        ttk.Separator(parent, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky="ew", pady=(10, 10))
        row += 1

        # Video-Varianten mit individuellen Privacy-Einstellungen
        ttk.Label(
            parent,
            text="Video-Varianten (Privacy pro Profil):",
            font=("Ubuntu", 12, "bold")
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 10), padx=5)
        row += 1

        for video in videos:
            snippet = video.get("snippet", {})
            stats = video.get("statistics", {})
            status = video.get("status", {})
            profile = self._detect_profile(video)
            video_id = video.get("id", "")

            # Profil-Label
            ttk.Label(
                parent,
                text=f"📹 {profile}",
                font=("Ubuntu", 11, "bold")
            ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(10, 5), padx=5)
            row += 1

            # Video-Details
            privacy_text = self._format_privacy(status.get("privacyStatus", ""))
            views = stats.get("viewCount", "0")
            likes = stats.get("likeCount", "0")

            details_text = f"Privacy: {privacy_text} • Views: {views} • Likes: {likes}"
            ttk.Label(
                parent,
                text=details_text,
                foreground="#555555"
            ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 5), padx=15)
            row += 1

            # Buttons für dieses Video
            button_frame = ttk.Frame(parent)
            button_frame.grid(row=row, column=0, columnspan=2, sticky="w", padx=15, pady=(0, 5))

            studio_url = f"https://studio.youtube.com/video/{video_id}/edit"
            watch_url = f"https://www.youtube.com/watch?v={video_id}"

            ttk.Button(
                button_frame,
                text="Studio öffnen",
                command=lambda url=studio_url: self._open_in_browser(url),
                bootstyle=PRIMARY
            ).pack(side=LEFT, padx=5)

            ttk.Button(
                button_frame,
                text="Video öffnen",
                command=lambda url=watch_url: self._open_in_browser(url),
                bootstyle=SECONDARY
            ).pack(side=LEFT, padx=5)

            ttk.Button(
                button_frame,
                text="⧉",
                width=3,
                command=lambda url=watch_url: self._copy_to_clipboard(url),
                bootstyle=SECONDARY
            ).pack(side=LEFT, padx=5)

            ttk.Button(
                button_frame,
                text="Video ersetzen",
                command=lambda vid=video_id: self._replace_video(vid),
                bootstyle=WARNING
            ).pack(side=LEFT, padx=5)

            ttk.Button(
                button_frame,
                text="🗑 Löschen",
                command=lambda vid=video_id, title=snippet.get("title", ""): self._delete_video(vid, title),
                bootstyle=DANGER
            ).pack(side=LEFT, padx=5)

            row += 1

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

        ttk.Button(
            button_frame,
            text="Video ersetzen",
            command=lambda vid=video.get("id"): self._replace_video(vid),
            bootstyle=WARNING
        ).pack(side=LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="🗑 Löschen",
            command=lambda vid=video.get("id"), title=snippet.get("title", ""): self._delete_video(vid, title),
            bootstyle=DANGER
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

    def _load_thumbnail_async(self, url: str, label: tk.Label, video_id, add_link_button: bool = False):
        """Lädt Thumbnail-Bild in separatem Thread und fügt Icons hinzu.

        Args:
            video_id: Kann eine einzelne Video-ID (str) oder eine Liste von IDs sein (für gruppierte Videos)
        """
        if not url:
            label.config(text="[kein Bild]")
            return

        cache_key = f"{url}_with_icon{'_link' if add_link_button else ''}"
        if cache_key in self.thumbnail_cache:
            label.config(image=self.thumbnail_cache[cache_key])
            label.image = self.thumbnail_cache[cache_key]
            if add_link_button:
                # Bei gruppierten Videos: Klick-Position bestimmt Funktion
                embed_id = video_id[0] if isinstance(video_id, list) else video_id
                label.bind("<Button-1>", lambda e: self._handle_grouped_thumbnail_click(e, embed_id, video_id))
            else:
                label.bind("<Button-1>", lambda e: self._upload_thumbnail(video_id))
            return

        def worker():
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                img = Image.open(BytesIO(response.content))
                img.thumbnail((160, 90), Image.Resampling.LANCZOS)

                # Icons hinzufügen
                img_with_icons = self._add_thumbnail_icons(img, add_link_button)

                photo = ImageTk.PhotoImage(img_with_icons)
                self.thumbnail_cache[cache_key] = photo
                self.after(0, lambda: self._apply_thumbnail(label, cache_key, video_id, add_link_button))
            except Exception:
                self.after(0, lambda: label.config(text="[Thumb Fehler]"))

        threading.Thread(target=worker, daemon=True).start()

    def _add_thumbnail_icons(self, img: Image.Image, add_link_button: bool) -> Image.Image:
        """Fügt Icons zum Thumbnail hinzu: Link-Button (oben rechts) + Upload-Icon (unten rechts)."""
        img = img.copy()

        icon_size = 28
        padding = 4

        # Konvertiere zu RGBA
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        # Link-Button oben rechts (🔗)
        if add_link_button:
            link_icon = self._create_link_icon(icon_size)
            x = img.width - icon_size - padding
            y = padding
            if link_icon.mode == 'RGBA':
                img.paste(link_icon, (x, y), link_icon)
            else:
                img.paste(link_icon, (x, y))

        # Upload-Icon unten rechts (📤) - schreibszene.ch orange
        upload_icon = load_upload_icon(size=icon_size, bg_color='#f7b33b')
        x = img.width - icon_size - padding
        y = img.height - icon_size - padding
        if upload_icon.mode == 'RGBA':
            img.paste(upload_icon, (x, y), upload_icon)
        else:
            img.paste(upload_icon, (x, y))

        # Zurück zu RGB
        if img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background

        return img

    def _create_link_icon(self, size: int) -> Image.Image:
        """Erstellt ein Material Design Link-Icon mit blauem Hintergrund."""
        icon = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(icon)

        # Blauer Kreis als Hintergrund (schreibszene.ch brightblue)
        draw.ellipse([0, 0, size, size], fill='#0eb1d2')

        # Weißes Material Design Link-Symbol (Kettenglied)
        link_color = (255, 255, 255, 255)
        margin = size // 5
        thickness = 2

        # Material Design Link: Zwei abgerundete Kettenglied-Formen
        # Linkes Glied (schräg links-oben)
        left_x1 = margin
        left_y1 = margin + 2
        left_x2 = size // 2 - 1
        left_y2 = margin + 2 + thickness
        draw.rectangle([left_x1, left_y1, left_x2, left_y2], fill=link_color)

        # Rechtes Glied (schräg rechts-unten)
        right_x1 = size // 2 + 1
        right_y1 = size - margin - thickness - 2
        right_x2 = size - margin
        right_y2 = size - margin - 2
        draw.rectangle([right_x1, right_y1, right_x2, right_y2], fill=link_color)

        # Verbindungslinien vertikal
        draw.rectangle([margin, left_y1, margin + thickness, size // 2], fill=link_color)
        draw.rectangle([size - margin - thickness, size // 2, size - margin, right_y2], fill=link_color)

        return icon

    def _add_upload_icon(self, img: Image.Image) -> Image.Image:
        """Fügt Upload-Icon aus SVG unten rechts im Thumbnail ein."""
        # Erstelle eine Kopie
        img = img.copy()

        # Lade Upload-Icon (weiß auf schreibszene.ch orange)
        icon_size = 28
        upload_icon = load_upload_icon(size=icon_size, bg_color='#f7b33b')

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

    def _apply_thumbnail(self, label: tk.Label, cache_key: str, video_id, add_link_button: bool = False):
        """Setzt zwischengespeichertes Thumbnail auf Label.

        Args:
            video_id: Kann eine einzelne Video-ID (str) oder eine Liste von IDs sein (für gruppierte Videos)
        """
        photo = self.thumbnail_cache.get(cache_key)
        if photo:
            label.config(image=photo)
            label.image = photo
            if add_link_button:
                # Bei gruppierten Videos: Klick-Position bestimmt Funktion
                embed_id = video_id[0] if isinstance(video_id, list) else video_id
                label.bind("<Button-1>", lambda e: self._handle_grouped_thumbnail_click(e, embed_id, video_id))
            else:
                label.bind("<Button-1>", lambda e: self._upload_thumbnail(video_id))

    def _handle_grouped_thumbnail_click(self, event, embed_id: str, all_video_ids):
        """Behandelt Klick auf Thumbnail mit mehreren Icons.

        Args:
            event: Klick-Event mit x/y-Koordinaten
            embed_id: Video-ID für Embed-Link (einzelne ID)
            all_video_ids: Liste aller Video-IDs für Thumbnail-Upload
        """
        # Icon-Dimensionen (müssen mit _add_thumbnail_icons übereinstimmen)
        icon_size = 28
        padding = 4

        # Label-Größe ermitteln
        label_width = event.widget.winfo_width()
        label_height = event.widget.winfo_height()

        # Klick-Position
        click_x = event.x
        click_y = event.y

        # Link-Icon: oben rechts
        link_x1 = label_width - icon_size - padding
        link_y1 = padding
        link_x2 = label_width - padding
        link_y2 = padding + icon_size

        # Upload-Icon: unten rechts
        upload_x1 = label_width - icon_size - padding
        upload_y1 = label_height - icon_size - padding
        upload_x2 = label_width - padding
        upload_y2 = label_height - padding

        # Prüfe ob Link-Icon geklickt wurde
        if link_x1 <= click_x <= link_x2 and link_y1 <= click_y <= link_y2:
            self._copy_embed_url(embed_id)
        # Prüfe ob Upload-Icon geklickt wurde
        elif upload_x1 <= click_x <= upload_x2 and upload_y1 <= click_y <= upload_y2:
            self._upload_thumbnail(all_video_ids)
        # Ansonsten: Kopiere Embed-URL (Fallback für Klick außerhalb der Icons)
        else:
            self._copy_embed_url(embed_id)

    def _copy_embed_url(self, video_id: str):
        """Kopiert Embed-URL in Zwischenablage."""
        embed_url = f"https://www.youtube.com/embed/{video_id}"
        self._copy_to_clipboard(embed_url)

    def _open_video_url(self, video_id: str):
        """Öffnet Embed-URL im Browser (für iFrame-Nutzung)."""
        embed_url = f"https://www.youtube.com/embed/{video_id}"
        self._open_in_browser(embed_url)

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

    def _upload_thumbnail(self, video_id):
        """Lädt ein manuell ausgewähltes Thumbnail zu YouTube hoch.

        Args:
            video_id: Kann eine einzelne Video-ID (str) oder eine Liste von IDs sein (für gruppierte Videos)
        """
        if not video_id:
            return

        # Bei Liste: Verwende erste ID für initial_dir
        first_id = video_id[0] if isinstance(video_id, list) else video_id
        initial_dir = get_source_folder(first_id) or str(Path.home())

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

        # Bei mehreren Videos: Bestätigung einholen
        video_ids = video_id if isinstance(video_id, list) else [video_id]
        if len(video_ids) > 1:
            confirm = messagebox.askyesno(
                "Thumbnail für mehrere Videos",
                f"Möchtest du dieses Thumbnail für alle {len(video_ids)} Videos hochladen?"
            )
            if not confirm:
                return

        self.status_label.config(text="Thumbnail-Upload gestartet...")
        self.thumbnail_cache.clear()

        # Upload für alle Video-IDs
        success_count = 0
        error_count = 0

        for vid in video_ids:
            try:
                upload_video_thumbnail(vid, file_path)
                success_count += 1
            except (UploadError, Exception) as e:
                error_count += 1
                print(f"Fehler beim Thumbnail-Upload für {vid}: {e}")

        # Status-Meldung
        if error_count == 0:
            self.status_label.config(text=f"Thumbnail für {success_count} Video(s) aktualisiert")
        else:
            self.status_label.config(text=f"{success_count} erfolgreich, {error_count} Fehler")

        self._load_assets()

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

    def _save_grouped_metadata(self, videos: List[Dict[str, Any]], title: str, description: str, tags: str):
        """Speichert gemeinsame Metadaten für alle Videos in einer Gruppe."""
        if not videos:
            return

        tags_list = [t.strip() for t in tags.split(",") if t.strip()]

        # Aktualisiere alle Videos in der Gruppe
        success_count = 0
        error_count = 0

        self.status_label.config(text=f"Aktualisiere {len(videos)} Videos...")

        for video in videos:
            video_id = video.get("id")
            current_privacy = video.get("status", {}).get("privacyStatus", "unlisted")

            try:
                update_video_metadata(
                    video_id=video_id,
                    title=title.strip(),
                    description=description,
                    privacy_status=current_privacy,  # Privacy bleibt individuell
                    tags=tags_list,
                    publish_at=None
                )
                success_count += 1
            except Exception as e:
                error_count += 1
                print(f"Fehler beim Aktualisieren von {video_id}: {e}")

        if error_count == 0:
            self.status_label.config(text=f"Alle {success_count} Videos aktualisiert")
        else:
            self.status_label.config(text=f"{success_count} erfolgreich, {error_count} Fehler")

        self._load_assets()

    def _replace_video(self, video_id: str):
        """Ersetzt die Video-Datei eines bestehenden Videos."""
        if not video_id:
            return

        # Warnung anzeigen
        confirm = messagebox.askyesno(
            "Video ersetzen",
            "WARNUNG: Diese Aktion ersetzt die Video-Datei des bestehenden Videos.\n\n"
            "Die URL, Titel, Beschreibung und Statistiken bleiben erhalten,\n"
            "aber der Video-Inhalt wird durch eine neue Datei ersetzt.\n\n"
            "Möchten Sie fortfahren?"
        )
        if not confirm:
            return

        # Datei auswählen
        initial_dir = get_source_folder(video_id) or str(Path.home())
        file_path = filedialog.askopenfilename(
            title="Neue Video-Datei auswählen",
            filetypes=[
                ("Video-Dateien", "*.mp4 *.avi *.mov *.mkv"),
                ("Alle Dateien", "*.*")
            ],
            initialdir=initial_dir
        )
        if not file_path:
            return

        # Upload in separatem Thread
        self.status_label.config(text="Video-Ersetzung gestartet...")

        def worker():
            try:
                def progress_cb(current, total):
                    percent = int((current / total) * 100)
                    self.after(0, lambda: self.status_label.config(
                        text=f"Video-Upload: {percent}% ({current // 1024 // 1024}MB / {total // 1024 // 1024}MB)"
                    ))

                replace_video_file(video_id, file_path, progress_callback=progress_cb)
                self.after(0, lambda: self.status_label.config(text="Video erfolgreich ersetzt – Aktualisiere Liste..."))
                self.after(0, self._load_assets)
            except UploadError as e:
                self.after(0, lambda: messagebox.showerror("YouTube-Fehler", str(e)))
                self.after(0, lambda: self.status_label.config(text="Fehler beim Video-Ersatz"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Fehler", str(e)))
                self.after(0, lambda: self.status_label.config(text="Fehler beim Video-Ersatz"))

        threading.Thread(target=worker, daemon=True).start()

    def _update_video_flags(self, video_id: str, made_for_kids: bool, embeddable: bool):
        """Aktualisiert ForKids und Embeddable Flags für ein Video."""
        if not video_id:
            return

        self.status_label.config(text="Aktualisiere Video-Einstellungen...")

        def worker():
            try:
                from app.youtube_assets import update_video_status_flags
                update_video_status_flags(video_id, made_for_kids, embeddable)
                self.after(0, lambda: self.status_label.config(text="Video-Einstellungen aktualisiert"))
            except Exception as e:
                self.after(0, lambda: self.status_label.config(text=f"Fehler: {e}"))

        threading.Thread(target=worker, daemon=True).start()

    def _update_grouped_video_flags(self, videos: List[Dict[str, Any]], made_for_kids: bool, embeddable: bool):
        """Aktualisiert ForKids und Embeddable Flags für alle Videos in einer Gruppe."""
        if not videos:
            return

        self.status_label.config(text=f"Aktualisiere {len(videos)} Videos...")

        def worker():
            success_count = 0
            error_count = 0

            try:
                from app.youtube_assets import update_video_status_flags
                for video in videos:
                    video_id = video.get("id")
                    try:
                        update_video_status_flags(video_id, made_for_kids, embeddable)
                        success_count += 1
                    except Exception as e:
                        error_count += 1
                        print(f"Fehler bei {video_id}: {e}")

                if error_count == 0:
                    self.after(0, lambda: self.status_label.config(text=f"Alle {success_count} Videos aktualisiert"))
                else:
                    self.after(0, lambda: self.status_label.config(text=f"{success_count} OK, {error_count} Fehler"))
            except Exception as e:
                self.after(0, lambda: self.status_label.config(text=f"Fehler: {e}"))

        threading.Thread(target=worker, daemon=True).start()

    def _delete_grouped_videos(self, videos: list, title: str):
        """Löscht alle Videos einer Gruppe permanent von YouTube."""
        if not videos:
            return

        video_count = len(videos)
        video_ids = [v["id"] for v in videos]

        # Erstelle Liste der Varianten für Anzeige
        variants_info = []
        for v in videos:
            privacy = v.get("status", {}).get("privacyStatus", "unbekannt")
            vid = v["id"]
            variants_info.append(f"  • {privacy}: {vid}")
        variants_text = "\n".join(variants_info)

        # Doppelte Bestätigung wegen permanenter Löschung
        confirm1 = messagebox.askyesno(
            "Alle Videos löschen",
            f"WARNUNG: {video_count} Videos permanent löschen?\n\n"
            f"Titel: {title}\n\n"
            f"Videos:\n{variants_text}\n\n"
            f"Diese Aktion kann NICHT rückgängig gemacht werden!"
        )
        if not confirm1:
            return

        confirm2 = messagebox.askyesno(
            "Wirklich alle löschen?",
            f"Letzte Bestätigung:\n\n"
            f"Alle {video_count} Varianten von '{title}'\n"
            f"werden permanent gelöscht.\n\n"
            f"Fortfahren?"
        )
        if not confirm2:
            return

        # Lösche in separatem Thread
        self.status_label.config(text=f"Lösche {video_count} Videos...")

        def worker():
            deleted = 0
            errors = []
            for vid in video_ids:
                try:
                    delete_video(vid)
                    deleted += 1
                    self.after(0, lambda d=deleted: self.status_label.config(
                        text=f"Gelöscht: {d}/{video_count}..."
                    ))
                except Exception as e:
                    errors.append(f"{vid}: {e}")

            if errors:
                error_text = "\n".join(errors)
                self.after(0, lambda: messagebox.showwarning(
                    "Teilweise Fehler",
                    f"{deleted}/{video_count} Videos gelöscht.\n\nFehler:\n{error_text}"
                ))
            else:
                self.after(0, lambda: self.status_label.config(
                    text=f"Alle {video_count} Videos erfolgreich gelöscht"
                ))

            self.after(0, self._load_assets)

        threading.Thread(target=worker, daemon=True).start()

    def _delete_video(self, video_id: str, title: str):
        """Löscht ein Video permanent von YouTube."""
        if not video_id:
            return

        # Doppelte Bestätigung wegen permanenter Löschung
        confirm1 = messagebox.askyesno(
            "Video löschen",
            f"WARNUNG: Video permanent löschen?\n\n"
            f"Titel: {title}\n"
            f"Video-ID: {video_id}\n\n"
            f"Diese Aktion kann NICHT rückgängig gemacht werden!"
        )
        if not confirm1:
            return

        confirm2 = messagebox.askyesno(
            "Wirklich löschen?",
            f"Letzte Bestätigung:\n\n"
            f"Video '{title}' wird permanent gelöscht.\n\n"
            f"Fortfahren?"
        )
        if not confirm2:
            return

        # Lösche in separatem Thread
        self.status_label.config(text="Video wird gelöscht...")

        def worker():
            try:
                delete_video(video_id)
                self.after(0, lambda: self.status_label.config(text="Video erfolgreich gelöscht – Aktualisiere Liste..."))
                self.after(0, self._load_assets)
            except UploadError as e:
                self.after(0, lambda: messagebox.showerror("YouTube-Fehler", str(e)))
                self.after(0, lambda: self.status_label.config(text="Fehler beim Löschen"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Fehler", str(e)))
                self.after(0, lambda: self.status_label.config(text="Fehler beim Löschen"))

        threading.Thread(target=worker, daemon=True).start()
