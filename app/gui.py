"""
Haupt-GUI für YouTube-Upload-App.
Verwendet ttkbootstrap für moderne Optik und Ubuntu-Font.
"""

import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import threading
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from app.config import (
    DEFAULT_FONT_FAMILY,
    DEFAULT_FONT_SIZE,
    DEFAULT_THEME,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    WINDOW_MIN_WIDTH,
    WINDOW_MIN_HEIGHT,
    SUPPORTED_VIDEO_EXTS
)
from app.matching import (
    find_companion_files,
    find_companion_files_multi,
    validate_video_file,
    FileMatchingError
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
from app.uploader import upload, UploadError
from app.auth import AuthError


class YouTubeUploadApp:
    """Haupt-GUI-Klasse für YouTube-Upload-Tool."""

    def __init__(self, root: ttk.Window):
        self.root = root
        self.root.title("YouTube Upload Tool")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        # State-Variablen
        self.video_path: str | None = None
        self.srt_path: str | None = None
        self.json_path: str | None = None
        self.factsheet_data: dict | None = None
        self.profiles: dict = {}
        self.selected_profile: str | None = None

        # Lade Profile
        self._load_profiles()

        # GUI aufbauen
        self._create_widgets()
        self._update_upload_button_state()

    def _load_profiles(self):
        """Lädt Upload-Profile aus YAML."""
        try:
            self.profiles = load_profiles()
        except ProfileError as e:
            messagebox.showerror("Profil-Fehler", str(e))
            self.root.quit()

    def _create_widgets(self):
        """Erstellt alle GUI-Widgets."""
        # Main Container mit Padding
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=BOTH, expand=YES)

        # Titel
        title_label = ttk.Label(
            main_frame,
            text="YouTube Upload Tool",
            font=(DEFAULT_FONT_FAMILY, 18, "bold"),
            bootstyle=PRIMARY
        )
        title_label.pack(pady=(0, 20))

        # Video-Sektion
        self._create_video_section(main_frame)

        # Datei-Status-Sektion
        self._create_file_status_section(main_frame)

        # Profil-Sektion
        self._create_profile_section(main_frame)

        # Upload-Button-Sektion
        self._create_upload_section(main_frame)

    def _create_video_section(self, parent):
        """Erstellt Video-Auswahl-Sektion."""
        video_frame = ttk.Labelframe(
            parent,
            text="1. Video auswählen",
            padding=15,
            bootstyle=INFO
        )
        video_frame.pack(fill=X, pady=(0, 15))

        # Button zum Video-Auswählen
        self.video_button = ttk.Button(
            video_frame,
            text="📹 Video wählen",
            command=self._select_video,
            bootstyle=INFO,
            width=20
        )
        self.video_button.pack(side=LEFT, padx=(0, 10))

        # Label für ausgewähltes Video
        self.video_label = ttk.Label(
            video_frame,
            text="Kein Video ausgewählt",
            font=(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE),
            foreground="gray"
        )
        self.video_label.pack(side=LEFT, fill=X, expand=YES)

    def _create_file_status_section(self, parent):
        """Erstellt Datei-Status-Anzeige."""
        status_frame = ttk.Labelframe(
            parent,
            text="2. Automatisch gefundene Dateien",
            padding=15,
            bootstyle=SUCCESS
        )
        status_frame.pack(fill=BOTH, expand=YES, pady=(0, 15))

        # SRT-Status
        srt_row = ttk.Frame(status_frame)
        srt_row.pack(fill=X, pady=5)

        ttk.Label(
            srt_row,
            text="Untertitel (.srt):",
            font=(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE, "bold"),
            width=18
        ).pack(side=LEFT)

        self.srt_status_label = ttk.Label(
            srt_row,
            text="—",
            font=(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE),
            foreground="gray"
        )
        self.srt_status_label.pack(side=LEFT, fill=X, expand=YES)

        # JSON-Status
        json_row = ttk.Frame(status_frame)
        json_row.pack(fill=X, pady=5)

        ttk.Label(
            json_row,
            text="Metadaten (.json):",
            font=(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE, "bold"),
            width=18
        ).pack(side=LEFT)

        self.json_status_label = ttk.Label(
            json_row,
            text="—",
            font=(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE),
            foreground="gray"
        )
        self.json_status_label.pack(side=LEFT, fill=X, expand=YES)

    def _create_profile_section(self, parent):
        """Erstellt Profil-Auswahl-Sektion."""
        profile_frame = ttk.Labelframe(
            parent,
            text="3. Upload-Profil wählen",
            padding=15,
            bootstyle=WARNING
        )
        profile_frame.pack(fill=X, pady=(0, 15))

        # Profil-Dropdown
        profile_names = get_profile_names(self.profiles)

        self.profile_var = tk.StringVar()
        self.profile_dropdown = ttk.Combobox(
            profile_frame,
            textvariable=self.profile_var,
            values=profile_names,
            state="readonly",
            font=(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE),
            width=30
        )
        self.profile_dropdown.pack(side=LEFT, padx=(0, 10))

        if profile_names:
            self.profile_dropdown.current(0)
            self.selected_profile = profile_names[0]

        # Event-Binding für Profil-Wechsel
        self.profile_dropdown.bind("<<ComboboxSelected>>", self._on_profile_changed)

        # Info-Label für Profil-Beschreibung
        self.profile_info_label = ttk.Label(
            profile_frame,
            text="",
            font=(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE - 1),
            foreground="darkblue",
            wraplength=400
        )
        self.profile_info_label.pack(side=LEFT, fill=X, expand=YES)

        # Tooltip für Dropdown
        self._update_profile_tooltip()

    def _create_upload_section(self, parent):
        """Erstellt Upload-Button-Sektion."""
        upload_frame = ttk.Frame(parent)
        upload_frame.pack(fill=X, pady=(10, 0))

        self.upload_button = ttk.Button(
            upload_frame,
            text="🚀 Video hochladen",
            command=self._upload_video,
            bootstyle=SUCCESS,
            state=DISABLED,
            width=25
        )
        self.upload_button.pack(pady=10)

        # Progressbar (initial versteckt)
        self.progress_bar = ttk.Progressbar(
            upload_frame,
            mode='determinate',
            bootstyle=SUCCESS,
            length=400
        )
        self.progress_bar.pack(pady=5)
        self.progress_bar.pack_forget()  # Verstecke initial

        # Status-Label
        self.status_label = ttk.Label(
            upload_frame,
            text="",
            font=(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE),
            foreground="gray"
        )
        self.status_label.pack()

    def _select_video(self):
        """Öffnet Datei-Dialog zur Video-Auswahl."""
        filetypes = [
            ("Video-Dateien", " ".join(f"*{ext}" for ext in SUPPORTED_VIDEO_EXTS)),
            ("Alle Dateien", "*.*")
        ]

        file_path = filedialog.askopenfilename(
            title="Video auswählen",
            filetypes=filetypes
        )

        if not file_path:
            return

        # Validiere Video-Datei
        is_valid, error_msg = validate_video_file(file_path)
        if not is_valid:
            messagebox.showerror("Fehler", error_msg)
            return

        self.video_path = file_path
        self.video_label.config(
            text=Path(file_path).name,
            foreground="black"
        )

        # Suche passende Dateien
        self._find_companion_files()

    def _find_companion_files(self):
        """Sucht passende SRT- und JSON-Dateien mit Mehrfach-Auswahl."""
        srt_files, json_files = find_companion_files_multi(self.video_path)

        # SRT-Datei auswählen/setzen
        if len(srt_files) == 0:
            self.srt_path = None
            self.srt_status_label.config(
                text="✗ Nicht gefunden (optional)",
                foreground="orange"
            )
        elif len(srt_files) == 1:
            self.srt_path = srt_files[0]
            self.srt_status_label.config(
                text=f"✓ {Path(self.srt_path).name}",
                foreground="green"
            )
        else:
            # Mehrere SRT-Dateien → Auswahl-Dialog
            self.srt_path = self._show_file_selection_dialog(
                "SRT-Datei auswählen",
                "Mehrere Untertitel-Dateien gefunden. Bitte wähle eine:",
                srt_files
            )
            if self.srt_path:
                self.srt_status_label.config(
                    text=f"✓ {Path(self.srt_path).name}",
                    foreground="green"
                )
            else:
                self.srt_status_label.config(
                    text="✗ Keine ausgewählt",
                    foreground="orange"
                )

        # JSON-Datei auswählen/setzen
        if len(json_files) == 0:
            self.json_path = None
            self.json_status_label.config(
                text="✗ Nicht gefunden",
                foreground="red"
            )
            self.factsheet_data = None
        elif len(json_files) == 1:
            self.json_path = json_files[0]
            self._validate_factsheet()
        else:
            # Mehrere JSON-Dateien → Auswahl-Dialog
            self.json_path = self._show_file_selection_dialog(
                "JSON-Datei auswählen",
                "Mehrere Metadaten-Dateien gefunden. Bitte wähle eine:",
                json_files
            )
            if self.json_path:
                self._validate_factsheet()
            else:
                self.json_status_label.config(
                    text="✗ Keine ausgewählt",
                    foreground="red"
                )
                self.factsheet_data = None

        self._update_upload_button_state()

    def _show_file_selection_dialog(self, title, message, files):
        """Zeigt Auswahl-Dialog für mehrere Dateien."""
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry("600x400")
        dialog.transient(self.root)
        dialog.grab_set()

        selected_file = [None]  # Mutable container for result

        # Content Frame
        content = ttk.Frame(dialog, padding=20)
        content.pack(fill=BOTH, expand=YES)

        # Message
        ttk.Label(
            content,
            text=message,
            font=(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE),
            wraplength=550
        ).pack(pady=(0, 15))

        # Listbox mit Dateien
        list_frame = ttk.Frame(content)
        list_frame.pack(fill=BOTH, expand=YES, pady=(0, 15))

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=RIGHT, fill=Y)

        listbox = tk.Listbox(
            list_frame,
            font=(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE),
            yscrollcommand=scrollbar.set,
            height=10
        )
        listbox.pack(side=LEFT, fill=BOTH, expand=YES)
        scrollbar.config(command=listbox.yview)

        # Dateien einfügen
        for file_path in files:
            listbox.insert(tk.END, Path(file_path).name)

        # Default-Auswahl: Erste Datei
        listbox.selection_set(0)

        def on_select():
            selection = listbox.curselection()
            if selection:
                selected_file[0] = files[selection[0]]
                dialog.destroy()

        def on_cancel():
            selected_file[0] = None
            dialog.destroy()

        # Buttons
        button_frame = ttk.Frame(content)
        button_frame.pack(fill=X)

        ttk.Button(
            button_frame,
            text="Auswählen",
            command=on_select,
            bootstyle=SUCCESS,
            width=15
        ).pack(side=LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="Abbrechen",
            command=on_cancel,
            bootstyle=SECONDARY,
            width=15
        ).pack(side=LEFT, padx=5)

        # Doppelklick auf Listbox → Auswählen
        listbox.bind("<Double-Button-1>", lambda e: on_select())

        # Warte auf Dialog-Schließung
        dialog.wait_window()

        return selected_file[0]

    def _validate_factsheet(self):
        """Validiert JSON-Factsheet."""
        is_valid, data, error_msg = load_and_validate_factsheet(self.json_path)

        if is_valid:
            self.json_status_label.config(
                text=f"✓ {Path(self.json_path).name}",
                foreground="green"
            )
            self.factsheet_data = data
        else:
            self.json_status_label.config(
                text=f"✗ Validierung fehlgeschlagen",
                foreground="red"
            )
            self.factsheet_data = None
            messagebox.showerror("JSON-Validierung", error_msg)

    def _on_profile_changed(self, event=None):
        """Callback wenn Profil geändert wird."""
        self.selected_profile = self.profile_var.get()
        self._update_profile_tooltip()
        self._update_upload_button_state()

    def _update_profile_tooltip(self):
        """Aktualisiert Tooltip für Profil-Dropdown."""
        if self.selected_profile:
            description = get_profile_description(self.selected_profile, self.profiles)
            self.profile_info_label.config(text=description.strip())
            create_tooltip(self.profile_dropdown, description, delay=300)

    def _update_upload_button_state(self):
        """Aktiviert/Deaktiviert Upload-Button basierend auf Validierung."""
        can_upload = (
            self.video_path is not None and
            self.factsheet_data is not None and
            self.selected_profile is not None
        )

        if can_upload:
            self.upload_button.config(state=NORMAL)
            self.status_label.config(text="Bereit zum Upload", foreground="green")
        else:
            self.upload_button.config(state=DISABLED)
            self.status_label.config(text="Wähle Video und validiere Dateien", foreground="gray")

    def _upload_video(self):
        """Startet Video-Upload in separatem Thread."""

        def progress_callback(progress):
            """Callback für Upload-Fortschritt (thread-safe)."""
            # Verwende after() für thread-sichere GUI-Updates
            self.root.after(0, self._update_progress, progress)

        def upload_worker():
            """Worker-Funktion für Upload-Thread."""
            try:
                # Hole Profil-Daten
                profile_data = get_profile(self.selected_profile, self.profiles)

                # Upload durchführen
                result = upload(
                    video_path=self.video_path,
                    srt_path=self.srt_path,
                    factsheet_data=self.factsheet_data,
                    profile_data=profile_data,
                    progress_callback=progress_callback
                )

                # Erfolg über GUI-Thread melden
                self.root.after(0, self._upload_success, result)

            except (UploadError, ProfileError, AuthError) as e:
                # Fehler über GUI-Thread melden
                self.root.after(0, self._upload_error, e)

        # Status-Update & Progressbar zeigen
        self.status_label.config(text="Upload startet...", foreground="blue")
        self.upload_button.config(state=DISABLED)
        self.progress_bar.pack(pady=5)
        self.progress_bar['value'] = 0

        # Starte Upload in separatem Thread
        upload_thread = threading.Thread(target=upload_worker, daemon=True)
        upload_thread.start()

    def _update_progress(self, progress):
        """Aktualisiert Fortschrittsanzeige (thread-safe)."""
        self.progress_bar['value'] = progress * 100
        self.status_label.config(
            text=f"Upload läuft... {int(progress * 100)}%",
            foreground="blue"
        )

    def _upload_success(self, result):
        """Zeigt Erfolg nach Upload an."""
        self.progress_bar['value'] = 100
        self.status_label.config(text="Upload erfolgreich!", foreground="green")

        # Zeige Result-Dialog mit Copy-Buttons
        self._show_result_dialog(result)

        # Progressbar verstecken
        self.progress_bar.pack_forget()
        self._update_upload_button_state()

    def _upload_error(self, error):
        """Zeigt Fehler nach Upload an."""
        self.progress_bar.pack_forget()
        self.status_label.config(text="Upload fehlgeschlagen", foreground="red")

        # Spezifische Fehlerbehandlung
        error_msg = str(error)
        if "403" in error_msg or "quota" in error_msg.lower():
            error_msg += "\n\n💡 Tipp: YouTube API-Quota überschritten.\nSiehe docs/README_OAUTH.md für Details."
        elif "401" in error_msg or "invalid" in error_msg.lower():
            error_msg += "\n\n💡 Tipp: Token ungültig.\nLösche ~/.config/yt-upload/token.pickle und starte neu."

        messagebox.showerror("Upload-Fehler", error_msg)
        self._update_upload_button_state()

    def _show_result_dialog(self, result):
        """Zeigt Erfolgs-Dialog mit Copy-Buttons."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Upload erfolgreich!")
        dialog.geometry("500x300")
        dialog.transient(self.root)
        dialog.grab_set()

        # Content Frame
        content = ttk.Frame(dialog, padding=20)
        content.pack(fill=BOTH, expand=YES)

        # Success Icon und Titel
        ttk.Label(
            content,
            text="✅ Video erfolgreich hochgeladen!",
            font=(DEFAULT_FONT_FAMILY, 14, "bold"),
            bootstyle=SUCCESS
        ).pack(pady=(0, 20))

        # Video-ID
        id_frame = ttk.Frame(content)
        id_frame.pack(fill=X, pady=5)
        ttk.Label(id_frame, text="Video-ID:", font=(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE, "bold")).pack(side=LEFT)
        ttk.Label(id_frame, text=result.video_id).pack(side=LEFT, padx=5)

        # Watch-URL
        watch_frame = ttk.Frame(content)
        watch_frame.pack(fill=X, pady=10)
        ttk.Label(watch_frame, text="Watch-URL:", font=(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE, "bold")).pack(anchor=W)
        watch_entry = ttk.Entry(watch_frame, width=60)
        watch_entry.insert(0, result.watch_url)
        watch_entry.config(state="readonly")
        watch_entry.pack(fill=X, pady=5)

        ttk.Button(
            watch_frame,
            text="📋 Kopieren",
            command=lambda: self._copy_to_clipboard(result.watch_url, "Watch-URL kopiert!"),
            bootstyle=INFO,
            width=15
        ).pack()

        # Embed-URL
        embed_frame = ttk.Frame(content)
        embed_frame.pack(fill=X, pady=10)
        ttk.Label(embed_frame, text="Embed-URL:", font=(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE, "bold")).pack(anchor=W)
        embed_entry = ttk.Entry(embed_frame, width=60)
        embed_entry.insert(0, result.embed_url)
        embed_entry.config(state="readonly")
        embed_entry.pack(fill=X, pady=5)

        ttk.Button(
            embed_frame,
            text="📋 Kopieren",
            command=lambda: self._copy_to_clipboard(result.embed_url, "Embed-URL kopiert!"),
            bootstyle=INFO,
            width=15
        ).pack()

        # Schließen-Button
        ttk.Button(
            content,
            text="Schließen",
            command=dialog.destroy,
            bootstyle=PRIMARY,
            width=15
        ).pack(pady=20)

    def _copy_to_clipboard(self, text, message):
        """Kopiert Text in Zwischenablage."""
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status_label.config(text=message, foreground="green")


def run_app():
    """Startet die GUI-Anwendung."""
    app = ttk.Window(themename=DEFAULT_THEME)
    YouTubeUploadApp(app)
    app.mainloop()
