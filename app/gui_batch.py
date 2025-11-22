"""
GUI mit Batch-Upload-Funktionalität.
Erlaubt Auswahl mehrerer Videos und automatisches Matching.
"""

import os
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk as tkttk
from pathlib import Path
import threading
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from app.config import (
    DEFAULT_FONT_FAMILY,
    DEFAULT_FONT_SIZE,
    DEFAULT_THEME,
    SUPPORTED_VIDEO_EXTS,
    CLIENT_SECRETS_PATH,
    TOKEN_PATH,
    CHANNEL_PUBLIC_URL,
    CHANNEL_STUDIO_URL,
    YOUTUBE_RED,
    YOUTUBE_LOGO
)
from app.matching import (
    find_companion_files_multi,
    validate_video_file
)
from app.profiles import (
    load_profiles,
    get_profile_names,
    get_profile_description,
    get_profile,
    ProfileError
)
from app.factsheet_schema import load_and_validate_factsheet
from app.tooltips import create_tooltip
from app.uploader import upload, UploadError, UploadResult
from app.auth import AuthError, create_youtube_client
from app.quick_upload_dialog import QuickUploadDialog
from app.favorites import (
    load_favorites,
    save_favorites,
    get_default_favorites,
    load_profile_preferences,
    save_profile_preferences
)
from app.asset_manager import AssetManagerWindow
from app.svg_icons import load_youtube_icon, load_upload_icon, load_folder_icon
from app.youtube_assets import find_video_by_title, replace_video_file
from PIL import ImageTk
from app.config import COLORS

CHANNEL_PUBLIC_URL = "https://www.youtube.com/@SchreibszeneChProfil"
CHANNEL_STUDIO_URL = "https://studio.youtube.com/channel/UCHBvwrKQfEwEWt4bKF1p0mQ"
from app.companion import (
    check_ffmpeg_available,
    find_subtitle_streams,
    extract_subtitle_stream,
    generate_thumbnail,
    get_video_companion_files
)


def get_companion_status_string(video_item: 'VideoItem') -> str:
    """
    Erzeugt Unicode-String für Companion-Status mit Material Design Symbolen.

    Returns:
        String wie "● JSON ● SRT (ext) ● Video (soft) ● Thumb (sample)"
    """
    parts = []

    # JSON
    if video_item.companion.get("json"):
        parts.append("● JSON")
    else:
        parts.append("○ JSON")

    # SRT (external oder container)
    if video_item.companion.get("srt_external"):
        parts.append("● SRT (ext)")
    elif video_item.companion.get("srt_container"):
        parts.append("● SRT (cont)")
    else:
        parts.append("○ SRT")

    # Video-Varianten
    if video_item.softsubs_path and video_item.hardsubs_path:
        parts.append("● Video (soft+hard)")
    elif video_item.softsubs_path:
        parts.append("● Video (soft)")
    elif video_item.hardsubs_path:
        parts.append("● Video (hard)")
    else:
        parts.append("○ Video")

    # Thumbnail
    if video_item.companion.get("thumbnail_sample"):
        parts.append("● Thumb (sample)")
    elif video_item.companion.get("thumbnail_generated"):
        parts.append("● Thumb (gen)")
    else:
        parts.append("○ Thumb")

    return " ".join(parts)


def get_profiles_string(video_item: 'VideoItem') -> str:
    """
    Erzeugt String mit aktiven Profilen.

    Returns:
        String wie "neutral_embed, public_youtube" oder "—"
    """
    active = [name for name, selected in video_item.selected_profiles.items() if selected]

    if not active:
        return "—"

    return ", ".join(active)


def init_profile_selection(profiles: dict, video_item: 'VideoItem') -> Dict[str, bool]:
    """
    Initialisiert Profil-Auswahl basierend auf default_selected und Requirements.

    Args:
        profiles: Dict mit allen Profilen
        video_item: VideoItem mit Companion-Status

    Returns:
        Dict[profile_name, is_selected]
    """
    selection = {}

    for profile_name, profile_data in profiles.items():
        # Defaults aus Profil
        default_selected = profile_data.get('default_selected', False)
        requires_srt = profile_data.get('requires_srt', False)
        requires_json = profile_data.get('requires_json', True)

        # Prüfe ob Requirements erfüllt
        can_select = True
        if requires_json and not video_item.has_json:
            can_select = False
        if requires_srt and not video_item.has_srt:
            can_select = False

        # Setze Selection (nur wenn Requirements erfüllt UND default_selected)
        selection[profile_name] = default_selected and can_select

    return selection


@dataclass
class VideoItem:
    """Repräsentiert ein Video mit zugehörigen Dateien."""
    video_path: str
    srt_path: Optional[str] = None
    json_path: Optional[str] = None
    factsheet_data: Optional[Dict[str, Any]] = None
    thumbnail_path: Optional[str] = None
    status: str = "Bereit"  # Bereit, Läuft, Fertig, Fehler
    error_msg: str = ""

    # Neue: Spezialisierte Video-Varianten
    softsubs_path: Optional[str] = None  # Video mit Container-SRT
    hardsubs_path: Optional[str] = None  # Video mit eingebrannten Untertiteln

    # Companion-Status
    companion: Dict[str, bool] = None

    # Profil-Auswahl pro Video
    selected_profiles: Dict[str, bool] = None

    # Notizen (z.B. "SRT auto-extrahiert")
    notes: str = ""

    def __post_init__(self):
        """Initialisiert Defaults für mutable Felder."""
        if self.companion is None:
            self.companion = {
                "json": False,
                "srt_external": False,
                "srt_container": False,
                "thumbnail_sample": False,    # sample_*.png vorhanden
                "thumbnail_generated": False  # Aus Video generiert
            }
        if self.selected_profiles is None:
            self.selected_profiles = {}

    @property
    def video_name(self) -> str:
        return Path(self.video_path).name

    @property
    def has_srt(self) -> bool:
        return self.srt_path is not None

    @property
    def has_json(self) -> bool:
        return self.json_path is not None and self.factsheet_data is not None

    @property
    def is_ready(self) -> bool:
        """Video ist bereit wenn JSON vorhanden und mind. 1 Profil aktiv."""
        return self.has_json and any(self.selected_profiles.values())


class BatchUploadApp:
    """GUI für Batch-Upload mehrerer Videos."""

    THUMB_DISPLAY_WIDTH = 180

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("YouTube Upload Tool - Batch Mode")
        self.root.geometry("1000x700")
        self.root.minsize(900, 650)
        # className is already set in run_app() via tk.Tk(className=...)

        # State
        self.videos: List[VideoItem] = []
        self.profiles: dict = {}
        self.upload_running = False
        self.favorites: List[dict] = []
        self.ffmpeg_available = False
        self.profile_prefs: dict = {}
        self.video_rows: List[dict] = []
        self.initial_auth_done = False
        self.auth_check_running = False
        self.batch_progress = {"current": 0, "total": 0, "success": 0, "failure": 0}
        self.last_directory_selection = str(Path.home())
        self.asset_window = None

        # YouTube-Icon für Buttons
        self.youtube_icon = None
        self._load_youtube_icon()

        # Lade Profile & Favoriten
        self._load_profiles()
        self._load_favorites()
        self._check_ffmpeg()
        self.profile_prefs = load_profile_preferences()

        # GUI aufbauen
        self._create_widgets()
        self._ensure_initial_auth()

        # Close-Handler für sauberes Beenden
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _load_youtube_icon(self):
        """Lädt YouTube-Icon aus SVG für Buttons."""
        try:
            from PIL import ImageTk
            # Lade YouTube-Icon (weiß auf rotem Hintergrund)
            icon_img = load_youtube_icon(size=16, bg_color=YOUTUBE_RED)
            self.youtube_icon = ImageTk.PhotoImage(icon_img)
        except Exception as e:
            print(f"⚠ YouTube-Icon konnte nicht geladen werden: {e}")
            self.youtube_icon = None

    def _load_profiles(self):
        """Lädt Upload-Profile aus YAML."""
        try:
            self.profiles = load_profiles()
        except ProfileError as e:
            messagebox.showerror("Profil-Fehler", str(e))
            self.root.quit()

    def _load_favorites(self):
        """Lädt Favoriten-Verzeichnisse."""
        self.favorites = load_favorites()
        if not self.favorites:
            self.favorites = get_default_favorites()
            save_favorites(self.favorites)

    def _check_ffmpeg(self):
        """Prüft ffmpeg-Verfügbarkeit."""
        available, error = check_ffmpeg_available()
        self.ffmpeg_available = available
        if not available:
            print(f"⚠ ffmpeg nicht verfügbar: {error}")
            print("  Container-SRT und Thumbnail-Generierung deaktiviert.")

    def _create_widgets(self):
        """Erstellt GUI-Widgets."""
        self.main_frame = ttk.Frame(self.root, padding=20)
        self.main_frame.pack(fill=BOTH, expand=YES)

        # Favoriten-Leiste (ohne Titel-Label)
        self.favorites_frame = None
        self._create_favorites_bar(self.main_frame)

        # Video-Liste (Treeview)
        self._create_video_list(self.main_frame)

        # Upload-Button
        self._create_upload_section(self.main_frame)

    def _create_favorites_bar(self, parent):
        """Erstellt Favoriten-Leiste für schnellen Zugriff."""
        # Zerstöre alte Favoriten-Bar falls vorhanden
        if self.favorites_frame:
            self.favorites_frame.destroy()

        self.favorites_frame = ttk.Frame(parent)
        self.favorites_frame.pack(fill=X, pady=(0, 10))

        # Farbe für Rahmen und Buttons (szbrightblue)
        szbrightblue = COLORS["szbrightblue"]

        # Gemeinsamer Rahmen für alle 4 Favoriten (3 Favoriten + Ordner wählen)
        favorites_container = ttk.Labelframe(
            self.favorites_frame,
            text="Podcast-Bündel-Uploads",
            padding=5,
            bootstyle=PRIMARY  # Verwendet szbrightblue durch Theme
        )
        favorites_container.pack(side=LEFT, padx=(0, 10))

        # Erste 3 Favoriten
        for idx, fav in enumerate(self.favorites[:3]):
            btn_container = ttk.Frame(favorites_container)
            btn_container.pack(side=LEFT, padx=2)

            # Button-Label: Nur Verzeichnisname
            dir_name = Path(fav["path"]).name if Path(fav["path"]).exists() else fav["label"]

            # Haupt-Button (öffnet Ordner-Scan) - schmaler
            main_btn = ttk.Button(
                btn_container,
                text=dir_name,
                command=lambda p=fav["path"]: self._on_favorite_clicked(p),
                bootstyle=PRIMARY,
                width=10
            )
            main_btn.pack(side=LEFT, padx=(0, 1))

            # Einstellungs-Button mit Gear-Icon ⚙ - schmaler, größere Schrift
            settings_btn = ttk.Button(
                btn_container,
                text="⚙",
                command=lambda f=fav: self._configure_favorite(f),
                bootstyle=SECONDARY,
                width=2
            )
            settings_btn.pack(side=LEFT)

        # Ordner wählen mit Material Design Folder Icon
        folder_container = ttk.Frame(favorites_container)
        folder_container.pack(side=LEFT, padx=2)

        # Lade Folder-Icon
        folder_icon_pil = load_folder_icon(size=28, bg_color=szbrightblue)
        self.folder_icon = ImageTk.PhotoImage(folder_icon_pil)

        folder_btn = ttk.Button(
            folder_container,
            image=self.folder_icon,
            command=self._add_folders,
            bootstyle=PRIMARY
        )
        folder_btn.pack()

        # Einzel Upload Button (ohne Rahmen, auf gleicher Höhe)
        ttk.Button(
            self.favorites_frame,
            text="Einzel Upload",
            command=self._open_quick_upload,
            bootstyle=SUCCESS,
            padding=(10, 5)
        ).pack(side=LEFT, padx=(10, 0))

        # YouTube-Rahmen (rechts)
        youtube_container = ttk.Labelframe(
            self.favorites_frame,
            text="YouTube",
            padding=5,
            bootstyle=DANGER
        )
        youtube_container.pack(side=RIGHT)

        ttk.Button(
            youtube_container,
            text="Kanal",
            command=self._open_channel,
            bootstyle=DANGER,
            width=6
        ).pack(side=LEFT, padx=2)

        ttk.Button(
            youtube_container,
            text="Studio",
            command=self._open_studio,
            bootstyle=DANGER,
            width=6
        ).pack(side=LEFT, padx=2)

        ttk.Button(
            youtube_container,
            text="Videos",
            command=self._open_asset_manager,
            bootstyle=DANGER,
            width=6
        ).pack(side=LEFT, padx=2)


    def _create_video_list(self, parent):
        """Erstellt Video-Tabelle mit Thumbnails, Dateien und Profil-Checkboxen."""

        # Header mit "Liste leeren" Button rechts
        list_header = ttk.Frame(parent)
        list_header.pack(fill=X, pady=(0, 5))

        ttk.Button(
            list_header,
            text="× Liste leeren",
            command=self._clear_videos,
            bootstyle=SECONDARY
        ).pack(side=RIGHT)

        list_frame = ttk.Labelframe(
            parent,
            text="Videos",
            padding=15,
            bootstyle=SUCCESS
        )
        list_frame.pack(fill=BOTH, expand=YES, pady=(0, 15))

        # Canvas + Scrollbar für scrollbare Tabelle
        canvas = tk.Canvas(list_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient=VERTICAL, command=canvas.yview)
        self.video_table_frame = ttk.Frame(canvas)

        self.video_table_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.video_table_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=LEFT, fill=BOTH, expand=YES)
        scrollbar.pack(side=RIGHT, fill=Y)

        # Header-Row
        header_frame = ttk.Frame(self.video_table_frame)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        ttk.Label(header_frame, text="Thumbnail", font=(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE, "bold")).grid(row=0, column=0, padx=5, sticky="w")
        ttk.Label(header_frame, text="Video + Dateien", font=(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE, "bold")).grid(row=0, column=1, padx=5, sticky="w")
        ttk.Label(header_frame, text="Profile", font=(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE, "bold")).grid(row=0, column=2, padx=5, sticky="w")
        ttk.Label(header_frame, text="↻", font=(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE, "bold")).grid(row=0, column=3, padx=5)
        ttk.Label(header_frame, text="✕", font=(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE, "bold")).grid(row=0, column=4, padx=5)

        # Grid-Konfiguration
        self.video_table_frame.columnconfigure(0, weight=0, minsize=self.THUMB_DISPLAY_WIDTH + 20)   # Thumbnail
        self.video_table_frame.columnconfigure(1, weight=3, minsize=300)  # Video
        self.video_table_frame.columnconfigure(2, weight=2, minsize=200)  # Profile
        self.video_table_frame.columnconfigure(3, weight=0, minsize=60)   # Reload
        self.video_table_frame.columnconfigure(4, weight=0, minsize=60)   # Remove

        # Storage für Video-Rows
        self.video_rows = []  # Liste von dict mit widgets

    def _create_video_row(self, video: VideoItem, row_index: int):
        """Erstellt eine Row in der Video-Tabelle."""
        row_num = row_index + 1  # +1 wegen Header

        # Spalte 0: Thumbnail
        thumb_label = ttk.Label(self.video_table_frame, text="[Thumb]")
        thumb_label.grid(row=row_num, column=0, padx=5, pady=5, sticky="w")

        # Spalte 1: Video + Dateien mit File-Picker-Buttons
        video_info_frame = ttk.Frame(self.video_table_frame)
        video_info_frame.grid(row=row_num, column=1, padx=5, pady=5, sticky="w")

        # Video-Name
        video_name_label = ttk.Label(
            video_info_frame,
            text=video.video_name,
            font=(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE, "bold"),
            wraplength=400
        )
        video_name_label.pack(anchor=tk.W)

        # Status-Zeile mit File-Picker-Buttons für fehlende Dateien
        status_frame = ttk.Frame(video_info_frame)
        status_frame.pack(anchor=tk.W, pady=(2, 0))

        status_text = get_companion_status_string(video)
        status_label = ttk.Label(
            status_frame,
            text=status_text,
            font=(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE - 1)
        )
        status_label.pack(side=LEFT)

        # File-Picker-Buttons für fehlende Dateien
        if not video.has_json:
            ttk.Button(
                status_frame,
                text="📁",
                command=lambda v=video: self._pick_json_file(v),
                bootstyle=WARNING,
                width=3
            ).pack(side=LEFT, padx=2)

        if not video.has_srt and not video.softsubs_path:
            ttk.Button(
                status_frame,
                text="📁",
                command=lambda v=video: self._pick_srt_file(v),
                bootstyle=WARNING,
                width=3
            ).pack(side=LEFT, padx=2)

        # Notizen
        if video.notes:
            notes_label = ttk.Label(
                video_info_frame,
                text=video.notes,
                font=(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE - 2),
                foreground="gray",
                wraplength=400
            )
            notes_label.pack(anchor=tk.W, pady=(2, 0))

        # Spalte 2: Profile mit Checkboxen
        profile_frame = ttk.Frame(self.video_table_frame)
        profile_frame.grid(row=row_num, column=2, padx=5, pady=5, sticky="w")

        profile_widgets = {}
        for profile_name, profile_data in self.profiles.items():
            requires_srt = profile_data.get('requires_srt', False)
            requires_json = profile_data.get('requires_json', True)

            # Prüfe Verfügbarkeit
            is_available = True
            if requires_json and not video.has_json:
                is_available = False
            if requires_srt and not video.has_srt:
                is_available = False

            # Frame für Profil + Checkbox
            pf = ttk.Frame(profile_frame)
            pf.pack(anchor=tk.W, pady=2)

            if is_available:
                # Verfügbar: fett + Checkbox
                var = tk.BooleanVar(value=video.selected_profiles.get(profile_name, False))
                cb = ttk.Checkbutton(
                    pf,
                    text=profile_name,
                    variable=var,
                    command=lambda v=video, pn=profile_name, var=var: self._on_profile_check_toggled(v, pn, var),
                    bootstyle="success-square-toggle"
                )
                cb.pack(side=LEFT)
                profile_widgets[profile_name] = var
            else:
                # Nicht verfügbar: grau, keine Checkbox
                ttk.Label(
                    pf,
                    text=f"  {profile_name}",
                    foreground="gray"
                ).pack(side=LEFT)

        # Spalte 3: Reload-Button
        reload_btn = ttk.Button(
            self.video_table_frame,
            text="↻",
            command=lambda v=video: self._reload_video(v),
            bootstyle=SECONDARY,
            width=3
        )
        reload_btn.grid(row=row_num, column=3, padx=5, pady=5)

        # Spalte 4: Remove-Button
        remove_btn = ttk.Button(
            self.video_table_frame,
            text="✕",
            command=lambda v=video: self._remove_video(v),
            bootstyle=DANGER,
            width=3
        )
        remove_btn.grid(row=row_num, column=4, padx=5, pady=5)

        # Speichere Row-Widgets
        return {
            "thumb": thumb_label,
            "video": video_name_label,
            "profile_frame": profile_frame,
            "profile_vars": profile_widgets,
            "reload_btn": reload_btn,
            "remove_btn": remove_btn
        }

    def _on_profile_check_toggled(self, video: VideoItem, profile_name: str, var: tk.BooleanVar):
        """Callback wenn Profil-Checkbox getoggled wird."""
        video.selected_profiles[profile_name] = var.get()

        # Speichere Präferenz
        video_basename = Path(video.video_path).stem
        self.profile_prefs[video_basename] = video.selected_profiles.copy()
        save_profile_preferences(self.profile_prefs)

        self._update_upload_button_state()

    def _pick_json_file(self, video: VideoItem):
        """Öffnet File-Picker für manuelle JSON-Auswahl."""
        video_dir = str(Path(video.video_path).parent)

        json_path = filedialog.askopenfilename(
            title="YouTube-Profil-JSON auswählen",
            initialdir=video_dir,
            filetypes=[
                ("YouTube Profile", "*_yt_profile.json"),
                ("JSON Files", "*.json"),
                ("All Files", "*.*")
            ]
        )

        if json_path:
            # Validiere JSON
            is_valid, data, error_msg = load_and_validate_factsheet(json_path)
            if is_valid:
                video.json_path = json_path
                video.factsheet_data = data
                video.companion["json"] = True
                video.selected_profiles = init_profile_selection(self.profiles, video)
                self._update_video_list()
                self._update_upload_button_state()
            else:
                messagebox.showerror("JSON-Fehler", f"JSON-Validierung fehlgeschlagen:\n{error_msg}")

    def _pick_srt_file(self, video: VideoItem):
        """Öffnet File-Picker für manuelle SRT-Auswahl."""
        video_dir = str(Path(video.video_path).parent)

        srt_path = filedialog.askopenfilename(
            title="Untertitel-Datei auswählen",
            initialdir=video_dir,
            filetypes=[
                ("Subtitle Files", "*.srt"),
                ("All Files", "*.*")
            ]
        )

        if srt_path:
            video.srt_path = srt_path
            video.companion["srt_external"] = True
            video.selected_profiles = init_profile_selection(self.profiles, video)
            self._update_video_list()
            self._update_upload_button_state()

    def _reload_video(self, video: VideoItem):
        """Lädt Companion-Dateien für Video neu mit neuer Logik."""
        from app.companion import get_video_companion_files

        video_path = video.video_path

        # Neue Companion-Suche
        companions = get_video_companion_files(video_path)

        # JSON
        json_path = companions.get("json_file")
        factsheet_data = None
        if json_path:
            is_valid, data, error_msg = load_and_validate_factsheet(json_path)
            if is_valid:
                factsheet_data = data
                json_path = json_path  # Keep path
            else:
                json_path = None

        # SRT (externe Datei)
        srt_path = companions.get("srt_file")

        # Video-Varianten
        softsubs_path = companions.get("softsubs_file")
        hardsubs_path = companions.get("hardsubs_file")

        # Thumbnail
        thumbnail_path = companions.get("thumbnail_file")

        # Update VideoItem
        video.json_path = json_path
        video.factsheet_data = factsheet_data
        video.srt_path = srt_path
        video.softsubs_path = softsubs_path
        video.hardsubs_path = hardsubs_path
        video.thumbnail_path = thumbnail_path

        # Update Companion-Status
        video.companion["json"] = factsheet_data is not None
        video.companion["srt_external"] = srt_path is not None
        video.companion["thumbnail_sample"] = thumbnail_path is not None

        # Update Profil-Selection
        video.selected_profiles = init_profile_selection(self.profiles, video)

        # Starte Companion-Processing neu (Container-SRT-Extraktion, Thumbnail-Gen)
        if self.ffmpeg_available:
            threading.Thread(
                target=self._process_companions_worker,
                args=(video,),
                daemon=True
            ).start()
        else:
            self._update_video_list()
            self._update_upload_button_state()

    def _create_upload_section(self, parent):
        """Erstellt Upload-Button unten."""
        upload_frame = ttk.Frame(parent)
        upload_frame.pack(fill=X, pady=(15, 0))

        self.upload_button = ttk.Button(
            upload_frame,
            text="▸ Alle Videos hochladen",
            command=self._start_batch_upload,
            bootstyle=SUCCESS,
            state=DISABLED,
            width=30
        )
        self.upload_button.pack(side=LEFT)

        # Replace if exists Checkbox (default: aktiviert)
        self.replace_if_exists_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            upload_frame,
            text="Replace if exists (ersetzt vorhandene Videos mit gleichem Titel)",
            variable=self.replace_if_exists_var,
            bootstyle="success-round-toggle"
        ).pack(side=LEFT, padx=(15, 0))

        # Status
        self.status_label = ttk.Label(
            upload_frame,
            text="",
            font=(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE),
            foreground="gray"
        )
        self.status_label.pack(side=LEFT, padx=(15, 0))

    def _ensure_initial_auth(self):
        """Stellt sicher, dass OAuth mindestens einmal ausgeführt wird."""
        if self.initial_auth_done or self.auth_check_running:
            return

        self.auth_check_running = True
        threading.Thread(target=self._initial_auth_worker, daemon=True).start()

    def _initial_auth_worker(self):
        """Führt initiale Authentifizierung im Hintergrund aus."""
        self.root.after(
            0,
            lambda: self._set_status_message("Prüfe YouTube-Authentifizierung...", "orange")
        )

        try:
            create_youtube_client(CLIENT_SECRETS_PATH, TOKEN_PATH)
            self.initial_auth_done = True
            self.root.after(
                0,
                lambda: self._set_status_message("YouTube-Authentifizierung bereit.", "green")
            )
        except AuthError as e:
            self.root.after(
                0,
                lambda: messagebox.showerror("Auth-Fehler", f"YouTube-Login erforderlich:\n{e}")
            )
            self.root.after(
                0,
                lambda: self._set_status_message("Auth fehlgeschlagen – bitte erneut versuchen.", "red")
            )
        finally:
            self.auth_check_running = False

    def _set_status_message(self, text: str, color: str = "blue"):
        """Aktualisiert globale Statusanzeige."""
        if hasattr(self, "status_label"):
            self.status_label.config(text=text, foreground=color)

    def _open_asset_manager(self):
        """Öffnet separates Fenster mit bereits hochgeladenen Videos."""
        if self.asset_window and self.asset_window.winfo_exists():
            self.asset_window.lift()
            return

        self.asset_window = AssetManagerWindow(self)

    def _open_quick_upload(self):
        """Öffnet Quick Upload Dialog für einzelne Video-Uploads."""
        QuickUploadDialog(self)

    def _open_channel(self):
        """Öffnet den öffentlichen YouTube-Kanal im bevorzugten Browser."""
        self._open_in_browser(CHANNEL_PUBLIC_URL)

    def _open_studio(self):
        """Öffnet das YouTube Studio des Kanals im bevorzugten Browser."""
        self._open_in_browser(CHANNEL_STUDIO_URL)

    def _open_in_browser(self, url: str):
        """Hilfsfunktion zum Öffnen von URLs mit bevorzugtem Browser."""
        preferred = os.getenv("YOUTUBE_OAUTH_BROWSER") or os.getenv("BROWSER")
        if preferred:
            try:
                webbrowser.get(preferred).open(url)
                return
            except webbrowser.Error:
                pass
        webbrowser.open(url)

    def _add_videos_from_dir(self, start_dir: str):
        """Öffnet Datei-Dialog mit vorgegebenem Startverzeichnis."""
        self._add_videos(initial_dir=start_dir)

    def _on_favorite_clicked(self, path: str):
        """Favorit-Button öffnet Ordnerauswahl relativ zum Favoritenpfad."""
        base_path = Path(path)
        if not base_path.exists():
            messagebox.showerror("Ordner nicht gefunden", f"{path} existiert nicht.")
            return

        directories = self._select_directories(base_dir=str(base_path))
        if not directories:
            return

        added = False
        for directory in directories:
            if self._add_video_from_directory(directory):
                added = True

        if added:
            self._update_video_list()
            self._update_upload_button_state()

    def _configure_favorite(self, favorite: dict):
        """Konfiguriert Favoriten-Verzeichnis (unabhängig von Videos)."""
        new_path = filedialog.askdirectory(
            title=f"Stammverzeichnis für '{favorite['label']}' wählen",
            initialdir=favorite["path"] if Path(favorite["path"]).exists() else str(Path.home())
        )

        if new_path:
            # Update in favorites list
            for fav in self.favorites:
                if fav["label"] == favorite["label"]:
                    fav["path"] = new_path
                    break

            # Speichern
            save_favorites(self.favorites)

            # Favoriten-Bar neu erstellen (zeigt neuen Verzeichnisnamen)
            self._create_favorites_bar(self.main_frame)

            # Info
            dir_name = Path(new_path).name
            messagebox.showinfo(
                "Favorit aktualisiert",
                f"Button zeigt jetzt: {dir_name}\nPfad: {new_path}"
            )

    def _add_videos(self, initial_dir: str = None):
        """Fügt Videos zur Liste hinzu (Multi-Select)."""
        filetypes = [
            ("Video-Dateien", " ".join(f"*{ext}" for ext in SUPPORTED_VIDEO_EXTS)),
            ("Alle Dateien", "*.*")
        ]

        kwargs = {"title": "Videos auswählen", "filetypes": filetypes}
        if initial_dir:
            kwargs["initialdir"] = initial_dir

        file_paths = filedialog.askopenfilenames(**kwargs)

        if not file_paths:
            return

        added = False
        for video_path in file_paths:
            if self._add_video_from_path(video_path):
                added = True

        if added:
            self._update_video_list()
            self._update_upload_button_state()

    def _add_folders(self):
        """Öffnet Multi-Ordner-Dialog (global) und fügt jeweils neuestes Video hinzu."""
        directories = self._select_directories()
        if not directories:
            return

        added = False
        for directory in directories:
            if self._add_video_from_directory(directory):
                added = True

        if added:
            self._update_video_list()
            self._update_upload_button_state()

    def _select_directories(self, base_dir: str = None) -> List[str]:
        """Erlaubt Auswahl mehrerer Ordner (wiederholter Dialog)."""
        selected = []
        initial_dir = base_dir or self.last_directory_selection or str(Path.home())

        while True:
            directory = filedialog.askdirectory(
                title="Ordner mit Video-Dateien auswählen",
                initialdir=initial_dir,
                mustexist=True
            )
            if not directory:
                break

            selected.append(directory)
            initial_dir = directory
            self.last_directory_selection = directory

            if not messagebox.askyesno(
                "Weitere Ordner?",
                "Möchtest du einen weiteren Ordner hinzufügen?"
            ):
                break

        return selected

    def _add_video_from_directory(self, directory: str) -> bool:
        """Fügt neuestes Video eines Ordners hinzu."""
        dir_path = Path(directory)
        if not dir_path.exists():
            messagebox.showerror("Ordner nicht gefunden", str(directory))
            return False

        if not dir_path.is_dir():
            messagebox.showerror("Kein Ordner", f"{directory} ist kein Ordner.")
            return False

        video_candidates = []
        for ext in SUPPORTED_VIDEO_EXTS:
            video_candidates.extend(dir_path.glob(f"*{ext}"))

        if not video_candidates:
            messagebox.showwarning("Keine Videos gefunden", f"In {directory} wurden keine Video-Dateien entdeckt.")
            return False

        newest_video = max(video_candidates, key=lambda p: p.stat().st_mtime)
        return self._add_video_from_path(str(newest_video))

    def _add_video_from_path(self, video_path: str) -> bool:
        """Fügt einzelnes Video anhand Pfad hinzu."""
        if any(v.video_path == video_path for v in self.videos):
            return False

        is_valid, error_msg = validate_video_file(video_path)
        if not is_valid:
            messagebox.showerror("Fehler", f"{Path(video_path).name}:\n{error_msg}")
            return False

        companions = get_video_companion_files(video_path)

        json_path = companions.get("json_file")
        factsheet_data = None
        if json_path:
            is_valid, data, error_msg = load_and_validate_factsheet(json_path)
            if is_valid:
                factsheet_data = data
            else:
                messagebox.showerror("JSON-Fehler", f"{Path(json_path).name}:\n{error_msg}")
                json_path = None

        srt_path = companions.get("srt_file")
        softsubs_path = companions.get("softsubs_file")
        hardsubs_path = companions.get("hardsubs_file")
        thumbnail_path = companions.get("thumbnail_file")

        video_item = VideoItem(
            video_path=video_path,
            srt_path=srt_path,
            json_path=json_path,
            factsheet_data=factsheet_data,
            softsubs_path=softsubs_path,
            hardsubs_path=hardsubs_path,
            thumbnail_path=thumbnail_path
        )

        video_item.companion["json"] = factsheet_data is not None
        video_item.companion["srt_external"] = srt_path is not None
        video_item.companion["thumbnail_sample"] = thumbnail_path is not None

        video_basename = Path(video_path).stem
        if video_basename in self.profile_prefs:
            video_item.selected_profiles = self.profile_prefs[video_basename].copy()
        else:
            video_item.selected_profiles = init_profile_selection(self.profiles, video_item)

        self.videos.append(video_item)

        if self.ffmpeg_available:
            threading.Thread(
                target=self._process_companions_worker,
                args=(video_item,),
                daemon=True
            ).start()

        return True

    def _process_companions_worker(self, video: VideoItem):
        """
        Worker-Thread für Companion-Processing (Container-SRT, Thumbnail).
        Neue Logik: Extrahiere aus softsubs-Video wenn vorhanden.

        Args:
            video: VideoItem-Objekt
        """
        notes = []

        # 1. Prüfe Container-SRT (nur wenn kein externes SRT vorhanden)
        if not video.has_srt:
            # Bevorzuge softsubs-Video für SRT-Extraktion
            source_video = video.softsubs_path if video.softsubs_path else video.video_path

            success, stream_indices, error = find_subtitle_streams(source_video)

            if success and stream_indices:
                # Nutze ersten Stream
                stream_idx = stream_indices[0]
                success, output_path, error = extract_subtitle_stream(
                    source_video,
                    stream_idx
                )

                if success:
                    video.srt_path = output_path
                    video.companion["srt_container"] = True
                    if video.softsubs_path:
                        notes.append("SRT aus softsubs-Video extrahiert")
                    else:
                        notes.append("SRT aus Container extrahiert")

                    # Update Profil-Selection (jetzt mit SRT)
                    video.selected_profiles = init_profile_selection(self.profiles, video)
                else:
                    notes.append(f"SRT-Extraktion fehlgeschlagen: {error}")

        # 2. Generiere Thumbnail (falls kein sample vorhanden)
        if not video.companion.get("thumbnail_sample"):
            # Bevorzuge softsubs-Video für Thumbnail-Generierung
            source_video = video.softsubs_path if video.softsubs_path else video.video_path

            success, output_path, error = generate_thumbnail(source_video, time_seconds=3)

            if success:
                video.thumbnail_path = output_path
                video.companion["thumbnail_generated"] = True
                notes.append("Thumbnail generiert (t=3s)")
            else:
                notes.append(f"Thumbnail-Generierung fehlgeschlagen: {error}")

        # 3. Update GUI (thread-safe via after())
        if notes:
            if video.notes:
                video.notes += "; " + "; ".join(notes)
            else:
                video.notes = "; ".join(notes)

        self.root.after(0, self._update_video_list)
        self.root.after(0, self._update_upload_button_state)

    def _clear_videos(self):
        """Entfernt alle Videos aus der Liste."""
        self.videos.clear()
        self._update_video_list()
        self._update_upload_button_state()

    def _remove_video(self, video: VideoItem):
        """Entfernt ein einzelnes Video aus der Liste."""
        if self.upload_running:
            messagebox.showwarning("Upload aktiv", "Während eines laufenden Uploads können keine Videos entfernt werden.")
            return

        self.videos = [v for v in self.videos if v is not video]
        self._update_video_list()
        self._update_upload_button_state()

    def _update_video_list(self):
        """Aktualisiert Video-Tabelle."""
        # Lösche alte Rows (außer Header)
        for row_widgets in self.video_rows:
            for widget in row_widgets.values():
                if hasattr(widget, "destroy"):
                    widget.destroy()

        self.video_rows.clear()

        # Erstelle neue Rows
        for i, video in enumerate(self.videos):
            row_widgets = self._create_video_row(video, i)
            self.video_rows.append(row_widgets)

            # Thumbnail laden falls vorhanden
            if video.thumbnail_path and Path(video.thumbnail_path).exists():
                self.root.after(0, self._load_thumbnail, video, i)

        # Video Count wurde entfernt - keine Anzeige mehr nötig

    def _load_thumbnail(self, video: VideoItem, row_index: int):
        """Lädt Thumbnail-Bild für Video-Row."""
        try:
            from PIL import Image, ImageTk

            img = Image.open(video.thumbnail_path)
            target_width = self.THUMB_DISPLAY_WIDTH
            if img.width > 0:
                ratio = target_width / float(img.width)
                target_height = max(1, int(img.height * ratio))
                img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)

            # Update Label
            if row_index < len(self.video_rows):
                thumb_label = self.video_rows[row_index]["thumb"]
                thumb_label.config(image=photo, text="")
                thumb_label.image = photo  # Referenz halten

        except Exception as e:
            print(f"Fehler beim Laden von Thumbnail: {e}")

    def _update_upload_button_state(self):
        """Aktiviert/Deaktiviert Upload-Button."""
        can_upload = (
            len(self.videos) > 0 and
            any(v.is_ready for v in self.videos) and
            not self.upload_running
        )

        self.upload_button.config(state=NORMAL if can_upload else DISABLED)

    def _show_file_selection(self, title, files):
        """Zeigt Auswahl-Dialog für Dateien."""
        # Vereinfachter Dialog
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry("500x300")
        dialog.transient(self.root)
        dialog.grab_set()

        selected = [None]

        ttk.Label(dialog, text="Mehrere Dateien gefunden:", padding=15).pack()

        listbox = tk.Listbox(dialog, height=10)
        listbox.pack(fill=BOTH, expand=YES, padx=15, pady=5)

        for f in files:
            listbox.insert(END, Path(f).name)

        listbox.selection_set(0)

        def on_ok():
            sel = listbox.curselection()
            if sel:
                selected[0] = files[sel[0]]
            dialog.destroy()

        ttk.Button(dialog, text="OK", command=on_ok, bootstyle=SUCCESS).pack(pady=10)

        dialog.wait_window()
        return selected[0]

    def _start_batch_upload(self):
        """Startet Batch-Upload."""
        if self.upload_running:
            return

        if self.auth_check_running:
            messagebox.showinfo(
                "YouTube-Authentifizierung",
                "Bitte warte, bis die YouTube-Authentifizierung abgeschlossen ist."
            )
            return

        if not self.initial_auth_done:
            self._ensure_initial_auth()
            messagebox.showinfo(
                "YouTube-Authentifizierung",
                "YouTube-Login wird vorbereitet. Bitte Authentifizierung abschließen und erneut versuchen."
            )
            return

        self.upload_running = True
        self.upload_button.config(state=DISABLED)
        self.status_label.config(text="Upload läuft...", foreground="blue")

        # Starte Upload-Thread
        upload_thread = threading.Thread(target=self._batch_upload_worker, daemon=True)
        upload_thread.start()

    def _batch_upload_worker(self):
        """Worker für Multi-Profil-Batch-Upload."""
        try:
            # Erstelle Liste von (Video, Profil)-Paaren
            upload_pairs = []

            for video in self.videos:
                if not video.has_json:
                    continue  # Überspringe Videos ohne JSON

                for profile_name, is_selected in video.selected_profiles.items():
                    if not is_selected:
                        continue  # Profil nicht aktiviert

                    # Prüfe Requirements
                    profile_data = self.profiles.get(profile_name)
                    if not profile_data:
                        continue

                    requires_srt = profile_data.get('requires_srt', False)
                    requires_json = profile_data.get('requires_json', True)

                    # Skip wenn Requirements nicht erfüllt
                    if requires_json and not video.has_json:
                        self.root.after(
                            0,
                            self._append_video_status,
                            video,
                            f"○ {profile_name}: JSON fehlt"
                        )
                        continue

                    if requires_srt and not video.has_srt:
                        self.root.after(
                            0,
                            self._append_video_status,
                            video,
                            f"○ {profile_name}: SRT fehlt"
                        )
                        continue

                    upload_pairs.append((video, profile_name))

            total = len(upload_pairs)

            if total == 0:
                self.root.after(0, self._batch_upload_error, "Keine Videos mit aktivierten Profilen gefunden")
                return

            self.batch_progress = {"current": 0, "total": total, "success": 0, "failure": 0}
            success_results = []
            failure_count = 0

            # Upload jedes Pairs
            for i, (video, profile_name) in enumerate(upload_pairs, 1):
                # Status Update
                self.root.after(0, self._append_video_status, video, f"↻ {profile_name}: Läuft...")

                try:
                    profile_data = get_profile(profile_name, self.profiles)
                    status_cb, progress_cb = self._make_upload_callbacks(video, profile_name)

                    # Füge Thumbnail zu Factsheet hinzu, falls vorhanden
                    factsheet_with_thumbnail = video.factsheet_data.copy()
                    if video.thumbnail_path and 'thumbnail' not in factsheet_with_thumbnail:
                        factsheet_with_thumbnail['thumbnail'] = video.thumbnail_path

                    # Replace if exists: Suche vorhandenes Video mit gleichem Titel
                    video_id_to_replace = None
                    if self.replace_if_exists_var.get():
                        title = factsheet_with_thumbnail.get("snippet", {}).get("title", "")
                        if title:
                            try:
                                existing_video = find_video_by_title(title)
                                if existing_video:
                                    video_id_to_replace = existing_video.get("id")
                                    self.root.after(0, self._append_video_status, video, f"  → Video existiert, wird ersetzt (ID: {video_id_to_replace[:8]}...)")
                            except Exception as e:
                                # Fehler beim Suchen ignorieren, normaler Upload fortsetzen
                                print(f"⚠ Fehler beim Suchen des Videos: {e}")

                    # Wenn Replace-Modus und Video gefunden: Ersetze Video-Datei
                    if video_id_to_replace:
                        try:
                            # Ersetze Video-Datei
                            def replace_progress_cb(current, total):
                                percent = int((current / total) * 100)
                                progress_cb({"progress": percent, "total": 100})

                            replace_video_file(video_id_to_replace, video.video_path, progress_callback=replace_progress_cb)

                            # Erstelle UploadResult mit vorhandener Video-ID
                            from app.uploader import UploadResult
                            result = UploadResult(
                                video_id=video_id_to_replace,
                                video_path=video.video_path,
                                srt_path=video.srt_path,
                                profile=profile_name,
                                title=title
                            )
                        except Exception as replace_error:
                            # Falls Replace fehlschlägt, normalen Upload durchführen
                            self.root.after(0, self._append_video_status, video, f"  → Replace fehlgeschlagen, normaler Upload...")
                            result = upload(
                                video_path=video.video_path,
                                srt_path=video.srt_path,
                                factsheet_data=factsheet_with_thumbnail,
                                profile_data=profile_data,
                                progress_callback=progress_cb,
                                status_callback=status_cb
                            )
                    else:
                        # Normaler Upload
                        result = upload(
                            video_path=video.video_path,
                            srt_path=video.srt_path,
                            factsheet_data=factsheet_with_thumbnail,
                            profile_data=profile_data,
                            progress_callback=progress_cb,
                            status_callback=status_cb
                        )
                    success_results.append(result)
                    self.batch_progress["success"] += 1
                    self._write_upload_log(video, profile_name, success=True, result=result)

                    self.root.after(
                        0,
                        self._replace_last_video_status,
                        video,
                        f"● {profile_name}: {result.video_id[:8]}..."
                    )

                except Exception as e:
                    failure_count += 1
                    self.batch_progress["failure"] += 1
                    error_msg = str(e)
                    self._write_upload_log(video, profile_name, success=False, error_message=error_msg)
                    self.root.after(
                        0,
                        self._replace_last_video_status,
                        video,
                        f"× {profile_name}: {error_msg[:30]}..."
                    )

                # Gesamtfortschritt
                self.batch_progress["current"] = i
                self.root.after(0, self._update_batch_status, i, total)

            # Fertig
            self.root.after(0, self._batch_upload_complete, success_results, failure_count, total)

        except Exception as e:
            self.root.after(0, self._batch_upload_error, str(e))

    def _make_upload_callbacks(self, video: VideoItem, profile_name: str):
        """Erstellt Callbacks für Status- und Fortschrittsupdates des Uploads."""
        last_bucket = {"value": -1}

        def progress_cb(progress: float):
            percent = int(progress * 100)
            bucket = percent // 5
            if bucket == last_bucket["value"]:
                return
            last_bucket["value"] = bucket
            self.root.after(
                0,
                self._replace_last_video_status,
                video,
                f"↻ {profile_name}: Upload {percent}%"
            )

        def status_cb(event: str, payload: Dict[str, Any]):
            message = self._format_upload_status(profile_name, event, payload or {})
            if message:
                self.root.after(0, self._replace_last_video_status, video, message)

        return status_cb, progress_cb

    def _format_upload_status(self, profile_name: str, event: str, payload: Dict[str, Any]) -> Optional[str]:
        """Erzeugt lesbaren Status-Text für Upload-Events."""
        prefix = f"↻ {profile_name}: "

        if event == "auth_start":
            return prefix + "Authentifiziere..."
        if event == "auth_success":
            return prefix + "Authentifizierung OK"
        if event == "metadata_ready":
            status = payload.get("status") or "n/a"
            return prefix + f"Metadaten bereit ({status})"
        if event == "upload_start":
            filename = payload.get('filename', '')
            return prefix + f"Lade Video hoch: {filename}"
        if event == "upload_success":
            video_id = payload.get('video_id', 'n/a')
            return prefix + f"Video-Upload erfolgreich! (ID: {video_id[:8]}...)"
        if event == "captions_start":
            filename = payload.get('filename', '')
            return prefix + f"Lade Untertitel hoch: {filename}"
        if event == "captions_success":
            lang = payload.get("language", "de")
            return prefix + f"Untertitel-Upload erfolgreich ({lang})"
        if event == "captions_error":
            message = payload.get("message", "Fehler")
            return prefix + f"Untertitel-Fehler: {message[:40]}..."
        if event == "thumbnail_start":
            filename = payload.get('filename', '')
            return prefix + f"Lade Thumbnail hoch: {filename}"
        if event == "thumbnail_success":
            return prefix + "Thumbnail-Upload erfolgreich"
        if event == "thumbnail_error":
            message = payload.get("message", "Fehler")
            return prefix + f"Thumbnail-Fehler: {message[:40]}..."

        return None

    def _write_upload_log(self, video: VideoItem, profile_name: str, success: bool, result: UploadResult = None, error_message: str = ""):
        """Schreibt Upload-Ergebnis in Log-Datei im Video-Verzeichnis."""
        try:
            log_dir = Path(video.video_path).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "yt_upload.log"

            timestamp = datetime.now().isoformat(timespec="seconds")
            video_name = Path(video.video_path).name

            if success and result:
                lines = [
                    f"[{timestamp}] {video_name} [{profile_name}]",
                    "STATUS: SUCCESS",
                    f"WATCH: {result.watch_url}",
                    f"EMBED: {result.embed_url}",
                    f"VIDEO_ID: {result.video_id}",
                    ""
                ]
            else:
                error_preview = (error_message or "Unbekannter Fehler").strip()
                lines = [
                    f"[{timestamp}] {video_name} [{profile_name}]",
                    "STATUS: ERROR",
                    f"MESSAGE: {error_preview}",
                    ""
                ]

            with log_file.open("a", encoding="utf-8") as f:
                f.write("\n".join(lines))

        except Exception as log_error:
            print(f"⚠ Konnte Upload-Log nicht schreiben ({video.video_name}): {log_error}")

    def _update_video_status(self, video, status):
        """Aktualisiert Status eines Videos."""
        video.status = status
        self._update_video_list()

    def _append_video_status(self, video, new_status):
        """Fügt neuen Status zu Video-Status hinzu (Multi-Line)."""
        if video.status == "Bereit":
            video.status = new_status
        else:
            video.status += f"\n{new_status}"
        self._update_video_list()

    def _replace_last_video_status(self, video, new_status):
        """Ersetzt letzte Zeile des Video-Status (z.B. "Läuft..." → "● Fertig")."""
        lines = video.status.split("\n")
        if lines and lines[-1].startswith("↻"):  # "Läuft..." Marker
            lines[-1] = new_status
            video.status = "\n".join(lines)
        else:
            video.status = new_status
        self._update_video_list()

    def _update_batch_status(self, current, total):
        """Aktualisiert Batch-Upload-Status."""
        success = self.batch_progress.get("success", 0)
        failure = self.batch_progress.get("failure", 0)
        self.status_label.config(
            text=f"Upload {current}/{total} – ✔ {success} / ✖ {failure}",
            foreground="blue"
        )

    def _batch_upload_complete(self, success_results=None, failure_count: int = 0, total: int = 0):
        """Callback nach erfolgreichem Batch-Upload."""
        self.upload_running = False
        success_results = success_results or []
        success_count = len(success_results)
        total = total or (success_count + failure_count)

        summary = f"Uploads fertig: {success_count}/{total} erfolgreich, {failure_count} Fehler"
        color = "green" if failure_count == 0 else "orange"
        self.status_label.config(text=summary, foreground=color)
        self._update_upload_button_state()
        if success_results:
            details = [summary, ""]
            for res in success_results:
                details.append(f"{res.title}: {res.watch_url}")
            messagebox.showinfo("Uploads abgeschlossen", "\n".join(details))
        else:
            messagebox.showwarning("Uploads abgeschlossen", summary)

    def _batch_upload_error(self, error_msg):
        """Callback bei Batch-Upload-Fehler."""
        self.upload_running = False
        self.status_label.config(text="Fehler beim Batch-Upload", foreground="red")
        self._update_upload_button_state()
        messagebox.showerror("Fehler", error_msg)

    def _on_close(self):
        """Beendet Anwendung ordnungsgemäß."""
        import sys
        self.root.quit()
        self.root.destroy()
        sys.exit(0)


def run_app():
    """Startet Batch-Upload-App."""
    # Use tk.Tk with className for proper desktop integration
    # (ttk.Window doesn't support className parameter)
    app = tk.Tk(className='YouTubeUploadTool')

    # Apply ttkbootstrap theme via Style
    style = ttk.Style(theme=DEFAULT_THEME)

    BatchUploadApp(app)
    app.mainloop()
