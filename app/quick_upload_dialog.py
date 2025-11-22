"""
Quick Upload Dialog für flexiblen, unkomplizierten Video-Upload.
Erlaubt Upload einzelner Videos ohne JSON-Metadaten.
"""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from app.config import SUPPORTED_VIDEO_EXTS
from app.matching import validate_video_file
from app.companion import get_video_companion_files, generate_thumbnail, check_ffmpeg_available
from app.uploader import upload, UploadError
from app.auth import create_youtube_client, AuthError


# YouTube Kategorien
YOUTUBE_CATEGORIES = {
    "22": "People & Blogs",
    "10": "Music",
    "23": "Comedy",
    "24": "Entertainment",
    "25": "News & Politics",
    "26": "How-to & Style",
    "27": "Education",
    "28": "Science & Technology",
    "1": "Film & Animation",
    "2": "Autos & Vehicles",
    "15": "Pets & Animals",
    "17": "Sports",
    "20": "Gaming",
}

# Sprachen
LANGUAGES = {
    "de": "Deutsch",
    "de-CH": "Deutsch (Schweiz)",
    "en": "English",
    "fr": "Français",
    "it": "Italiano",
    "es": "Español",
}


@dataclass
class QuickVideoItem:
    """Minimale Video-Info für Quick-Upload."""
    video_path: str
    srt_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    status: str = "Bereit"


class QuickUploadDialog(tk.Toplevel):
    """Dialog für schnellen Upload einzelner Videos ohne JSON-Metadaten."""

    def __init__(self, owner):
        parent = getattr(owner, "root", owner)
        super().__init__(parent)
        self.owner = owner

        self.title("Quick Upload - Einzelne Videos hochladen")
        self.geometry("800x650")
        self.minsize(700, 550)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.videos: List[QuickVideoItem] = []
        self.is_uploading = False
        self.ffmpeg_available, _ = check_ffmpeg_available()

        self._build_ui()

    def _build_ui(self):
        """Erstellt Dialog-UI."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # Header
        header = ttk.Frame(self, padding=(15, 10))
        header.grid(row=0, column=0, sticky="ew")

        ttk.Label(
            header,
            text="Quick Upload",
            font=("Ubuntu", 16, "bold")
        ).pack(side=LEFT)

        # Video-Auswahl Sektion
        video_section = ttk.Labelframe(
            self,
            text="1. Videos auswählen",
            padding=15
        )
        video_section.grid(row=1, column=0, sticky="nsew", padx=15, pady=(5, 10))
        video_section.columnconfigure(0, weight=1)
        video_section.rowconfigure(1, weight=1)

        btn_frame = ttk.Frame(video_section)
        btn_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        ttk.Button(
            btn_frame,
            text="Videos hinzufügen...",
            command=self._add_videos,
            bootstyle=PRIMARY
        ).pack(side=LEFT, padx=(0, 5))

        ttk.Button(
            btn_frame,
            text="Liste leeren",
            command=self._clear_videos,
            bootstyle=SECONDARY
        ).pack(side=LEFT)

        # Video-Liste
        list_container = ttk.Frame(video_section)
        list_container.grid(row=1, column=0, sticky="nsew")
        list_container.columnconfigure(0, weight=1)
        list_container.rowconfigure(0, weight=1)

        self.video_listbox = tk.Listbox(
            list_container,
            height=8,
            font=("Ubuntu", 10)
        )
        scrollbar = ttk.Scrollbar(
            list_container,
            orient=VERTICAL,
            command=self.video_listbox.yview
        )
        self.video_listbox.configure(yscrollcommand=scrollbar.set)

        self.video_listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Upload-Einstellungen Sektion
        settings_section = ttk.Labelframe(
            self,
            text="2. Upload-Einstellungen",
            padding=15
        )
        settings_section.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 10))
        settings_section.columnconfigure(1, weight=1)

        # Privacy
        row = 0
        ttk.Label(settings_section, text="Sichtbarkeit:").grid(
            row=row, column=0, sticky="w", pady=5
        )
        self.privacy_var = tk.StringVar(value="unlisted")
        privacy_frame = ttk.Frame(settings_section)
        privacy_frame.grid(row=row, column=1, sticky="w", padx=(10, 0))

        ttk.Radiobutton(
            privacy_frame,
            text="Öffentlich",
            variable=self.privacy_var,
            value="public"
        ).pack(side=LEFT, padx=(0, 10))

        ttk.Radiobutton(
            privacy_frame,
            text="Nicht gelistet",
            variable=self.privacy_var,
            value="unlisted"
        ).pack(side=LEFT, padx=(0, 10))

        ttk.Radiobutton(
            privacy_frame,
            text="Privat",
            variable=self.privacy_var,
            value="private"
        ).pack(side=LEFT)

        # Kategorie
        row += 1
        ttk.Label(settings_section, text="Kategorie:").grid(
            row=row, column=0, sticky="w", pady=5
        )
        self.category_var = tk.StringVar(value="27")
        category_combo = ttk.Combobox(
            settings_section,
            textvariable=self.category_var,
            state="readonly",
            width=30
        )
        category_combo['values'] = [
            f"{cat_id} - {cat_name}"
            for cat_id, cat_name in YOUTUBE_CATEGORIES.items()
        ]
        category_combo.set("27 - Education")
        category_combo.grid(row=row, column=1, sticky="w", padx=(10, 0))

        # Sprache
        row += 1
        ttk.Label(settings_section, text="Sprache:").grid(
            row=row, column=0, sticky="w", pady=5
        )
        self.language_var = tk.StringVar(value="de-CH")
        lang_combo = ttk.Combobox(
            settings_section,
            textvariable=self.language_var,
            state="readonly",
            width=30
        )
        lang_combo['values'] = [
            f"{lang_code} - {lang_name}"
            for lang_code, lang_name in LANGUAGES.items()
        ]
        lang_combo.set("de-CH - Deutsch (Schweiz)")
        lang_combo.grid(row=row, column=1, sticky="w", padx=(10, 0))

        # Companion-Optionen
        row += 1
        ttk.Label(settings_section, text="Automatisch:").grid(
            row=row, column=0, sticky="w", pady=5
        )
        auto_frame = ttk.Frame(settings_section)
        auto_frame.grid(row=row, column=1, sticky="w", padx=(10, 0))

        self.find_srt_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            auto_frame,
            text="SRT-Dateien suchen",
            variable=self.find_srt_var,
            bootstyle="success-round-toggle"
        ).pack(anchor="w")

        self.generate_thumb_var = tk.BooleanVar(value=True)
        thumb_text = "Thumbnail generieren (erstes Frame)" if self.ffmpeg_available else "Thumbnail generieren (ffmpeg fehlt)"
        thumb_check = ttk.Checkbutton(
            auto_frame,
            text=thumb_text,
            variable=self.generate_thumb_var,
            bootstyle="success-round-toggle"
        )
        if not self.ffmpeg_available:
            thumb_check.configure(state=DISABLED)
            self.generate_thumb_var.set(False)
        thumb_check.pack(anchor="w")

        # Titel-Vorlage
        row += 1
        ttk.Label(settings_section, text="Titel:").grid(
            row=row, column=0, sticky="w", pady=5
        )
        title_frame = ttk.Frame(settings_section)
        title_frame.grid(row=row, column=1, sticky="ew", padx=(10, 0))
        title_frame.columnconfigure(0, weight=1)

        self.use_filename_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            title_frame,
            text="Dateiname als Titel verwenden",
            variable=self.use_filename_var,
            bootstyle="success-round-toggle",
            command=self._toggle_custom_title
        ).grid(row=0, column=0, sticky="w")

        self.custom_title_entry = ttk.Entry(title_frame, state=DISABLED)
        self.custom_title_entry.grid(row=1, column=0, sticky="ew", pady=(5, 0))

        # Buttons
        button_frame = ttk.Frame(self, padding=15)
        button_frame.grid(row=3, column=0, sticky="ew")

        self.upload_btn = ttk.Button(
            button_frame,
            text="▸ Hochladen",
            command=self._start_upload,
            bootstyle=SUCCESS,
            state=DISABLED
        )
        self.upload_btn.pack(side=RIGHT, padx=(5, 0))

        ttk.Button(
            button_frame,
            text="Abbrechen",
            command=self._on_close,
            bootstyle=SECONDARY
        ).pack(side=RIGHT)

        # Status
        self.status_label = ttk.Label(
            button_frame,
            text="",
            foreground="gray"
        )
        self.status_label.pack(side=LEFT)

    def _toggle_custom_title(self):
        """Aktiviert/Deaktiviert Custom-Titel-Eingabe."""
        # Custom Titel nur aktivieren wenn:
        # 1. Checkbox nicht aktiviert UND
        # 2. Nur eine Datei ausgewählt
        if self.use_filename_var.get() or len(self.videos) != 1:
            self.custom_title_entry.configure(state=DISABLED)
        else:
            self.custom_title_entry.configure(state=NORMAL)

    def _add_videos(self):
        """Öffnet Video-Auswahl-Dialog."""
        filetypes = [
            ("Video-Dateien", " ".join(f"*{ext}" for ext in SUPPORTED_VIDEO_EXTS)),
            ("Alle Dateien", "*.*")
        ]

        file_paths = filedialog.askopenfilenames(
            title="Videos für Quick Upload auswählen",
            filetypes=filetypes
        )

        if not file_paths:
            return

        for video_path in file_paths:
            # Prüfe ob bereits hinzugefügt
            if any(v.video_path == video_path for v in self.videos):
                continue

            # Validiere Video
            is_valid, error_msg = validate_video_file(video_path)
            if not is_valid:
                messagebox.showwarning(
                    "Ungültige Datei",
                    f"{Path(video_path).name}:\n{error_msg}"
                )
                continue

            # Suche Companion-Dateien wenn gewünscht
            srt_path = None
            thumbnail_path = None

            if self.find_srt_var.get():
                companions = get_video_companion_files(video_path)
                srt_path = companions.get("srt_file")
                thumbnail_path = companions.get("thumbnail_file")

            # Generiere Thumbnail wenn gewünscht und nicht gefunden
            if self.generate_thumb_var.get() and not thumbnail_path and self.ffmpeg_available:
                try:
                    success, thumb_path, error = generate_thumbnail(
                        video_path,
                        time_seconds=0  # Erstes Frame
                    )
                    if success:
                        thumbnail_path = thumb_path
                except Exception as e:
                    print(f"⚠ Thumbnail-Generierung fehlgeschlagen: {e}")

            # Füge zur Liste hinzu
            video_item = QuickVideoItem(
                video_path=video_path,
                srt_path=srt_path,
                thumbnail_path=thumbnail_path
            )
            self.videos.append(video_item)

        self._update_video_list()

    def _update_video_list(self):
        """Aktualisiert Video-Listbox."""
        self.video_listbox.delete(0, tk.END)

        for video in self.videos:
            name = Path(video.video_path).name

            # Status-Indikatoren
            indicators = []
            if video.srt_path:
                indicators.append("SRT")
            if video.thumbnail_path:
                indicators.append("Thumb")

            indicator_str = f" [{', '.join(indicators)}]" if indicators else ""
            display_text = f"{name}{indicator_str} - {video.status}"

            self.video_listbox.insert(tk.END, display_text)

        # Update Button-Status
        self.upload_btn.configure(
            state=NORMAL if self.videos else DISABLED
        )

        # Update Titel-Eingabe (nur bei einer Datei aktivierbar)
        self._toggle_custom_title()

        # Update Status-Label
        count = len(self.videos)
        self.status_label.config(
            text=f"{count} Video{'s' if count != 1 else ''} ausgewählt"
        )

    def _clear_videos(self):
        """Leert Video-Liste."""
        if not self.videos:
            return

        if messagebox.askyesno(
            "Liste leeren",
            "Möchtest du alle Videos aus der Liste entfernen?"
        ):
            self.videos.clear()
            self._update_video_list()

    def _start_upload(self):
        """Startet Upload-Prozess."""
        if not self.videos:
            return

        if self.is_uploading:
            messagebox.showinfo("Upload läuft", "Es läuft bereits ein Upload.")
            return

        # Bestätige Upload
        count = len(self.videos)
        privacy_label = {
            "public": "öffentlich",
            "unlisted": "nicht gelistet",
            "private": "privat"
        }[self.privacy_var.get()]

        msg = (
            f"{count} Video{'s' if count != 1 else ''} als '{privacy_label}' hochladen?\n\n"
            f"Kategorie: {self.category_var.get()}\n"
            f"Sprache: {self.language_var.get()}"
        )

        if not messagebox.askyesno("Upload bestätigen", msg):
            return

        # Deaktiviere UI
        self.is_uploading = True
        self.upload_btn.configure(state=DISABLED)
        self.status_label.config(text="Upload läuft...", foreground="blue")

        # Starte Upload-Thread
        threading.Thread(
            target=self._upload_worker,
            daemon=True
        ).start()

    def _upload_worker(self):
        """Worker-Thread für Upload."""
        successful = 0
        failed = 0

        for idx, video in enumerate(self.videos, 1):
            # Update Status
            self.after(0, lambda i=idx: self._update_status(
                f"Upload {i}/{len(self.videos)}..."
            ))

            try:
                # Erstelle minimale Metadaten
                metadata = self._create_minimal_metadata(video)

                # Upload
                def progress_callback(progress):
                    percent = int(progress * 100)
                    self.after(0, lambda p=percent, i=idx: self._update_status(
                        f"Upload {i}/{len(self.videos)} - {p}%"
                    ))

                result = upload(
                    video_path=video.video_path,
                    factsheet_data=metadata,
                    profile_data={},
                    srt_path=video.srt_path,
                    progress_callback=progress_callback
                )

                # Erfolg
                video.status = f"✓ {result.video_id}"
                successful += 1

            except (UploadError, AuthError) as e:
                video.status = f"✗ Fehler: {str(e)[:30]}"
                failed += 1
            except Exception as e:
                video.status = f"✗ {str(e)[:30]}"
                failed += 1

            # Update Liste
            self.after(0, self._update_video_list)

        # Upload fertig
        self.after(0, lambda: self._upload_finished(successful, failed))

    def _create_minimal_metadata(self, video: QuickVideoItem) -> Dict[str, Any]:
        """Erstellt minimale Metadaten für Upload."""
        # Titel
        if self.use_filename_var.get() or len(self.videos) > 1:
            # Bei mehreren Dateien oder Dateiname-Option: Dateinamen verwenden
            # Ersetze - und _ durch Leerzeichen für bessere Lesbarkeit
            title = Path(video.video_path).stem
            title = title.replace('-', ' ').replace('_', ' ')
            # Entferne mehrfache Leerzeichen
            title = ' '.join(title.split())
        else:
            # Bei einer Datei: Custom Titel verwenden (falls angegeben)
            title = self.custom_title_entry.get()
            if not title:
                # Fallback: Dateiname mit Ersetzungen
                title = Path(video.video_path).stem
                title = title.replace('-', ' ').replace('_', ' ')
                title = ' '.join(title.split())

        # Kategorie-ID extrahieren
        category_text = self.category_var.get()
        category_id = category_text.split(" - ")[0] if " - " in category_text else "27"

        # Sprache extrahieren
        language_text = self.language_var.get()
        language_code = language_text.split(" - ")[0] if " - " in language_text else "de-CH"

        # Minimale Metadaten-Struktur
        metadata = {
            "snippet": {
                "title": title[:100],  # YouTube-Limit: 100 Zeichen
                "description": title,
                "categoryId": category_id
            },
            "status": {
                "privacyStatus": self.privacy_var.get(),
                "embeddable": True,
                "selfDeclaredMadeForKids": False
            },
            "language": language_code
        }

        # Thumbnail hinzufügen (falls vorhanden)
        if video.thumbnail_path:
            metadata["thumbnail"] = video.thumbnail_path

        return metadata

    def _update_status(self, text: str):
        """Aktualisiert Status-Label (Thread-safe)."""
        self.status_label.config(text=text)

    def _upload_finished(self, successful: int, failed: int):
        """Wird nach Upload-Ende aufgerufen."""
        self.is_uploading = False
        self.upload_btn.configure(state=NORMAL)

        # Status-Meldung
        if failed == 0:
            self.status_label.config(
                text=f"✓ {successful} Video{'s' if successful != 1 else ''} erfolgreich hochgeladen",
                foreground="green"
            )
            messagebox.showinfo(
                "Upload erfolgreich",
                f"{successful} Video{'s' if successful != 1 else ''} wurde{'n' if successful != 1 else ''} erfolgreich hochgeladen."
            )
        else:
            self.status_label.config(
                text=f"✓ {successful} / ✗ {failed}",
                foreground="orange"
            )
            messagebox.showwarning(
                "Upload abgeschlossen",
                f"Erfolgreich: {successful}\nFehlgeschlagen: {failed}\n\nBitte prüfe die Details in der Liste."
            )

    def _on_close(self):
        """Schließt Dialog."""
        if self.is_uploading:
            if not messagebox.askyesno(
                "Upload läuft",
                "Ein Upload läuft noch. Wirklich schließen?"
            ):
                return

        self.destroy()
