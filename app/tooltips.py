"""
Tooltip-Logik für Hover-Erklärungen in der GUI.
Zeigt zusätzliche Informationen beim Überfahren von Widgets.
"""

import tkinter as tk
from typing import Optional


class ToolTip:
    """
    Erstellt Tooltips für Tkinter-Widgets.
    Zeigt Text beim Hovern über dem Widget.
    """

    def __init__(self, widget: tk.Widget, text: str, delay: int = 500):
        """
        Args:
            widget: Das Widget, für das der Tooltip angezeigt werden soll
            text: Tooltip-Text
            delay: Verzögerung in Millisekunden vor Anzeige
        """
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip_window: Optional[tk.Toplevel] = None
        self.schedule_id: Optional[str] = None

        # Event-Bindings
        self.widget.bind("<Enter>", self._on_enter)
        self.widget.bind("<Leave>", self._on_leave)
        self.widget.bind("<Button>", self._on_leave)  # Verstecke bei Klick

    def _on_enter(self, event=None):
        """Widget wurde mit Maus betreten."""
        self._schedule_show()

    def _on_leave(self, event=None):
        """Widget wurde verlassen."""
        self._cancel_schedule()
        self._hide()

    def _schedule_show(self):
        """Plant Anzeige des Tooltips nach Verzögerung."""
        self._cancel_schedule()
        self.schedule_id = self.widget.after(self.delay, self._show)

    def _cancel_schedule(self):
        """Bricht geplante Anzeige ab."""
        if self.schedule_id:
            self.widget.after_cancel(self.schedule_id)
            self.schedule_id = None

    def _show(self):
        """Zeigt Tooltip-Fenster."""
        if self.tooltip_window or not self.text:
            return

        # Position des Widgets ermitteln
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

        # Tooltip-Fenster erstellen
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)  # Keine Fenster-Dekorationen
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        # Tooltip-Inhalt
        label = tk.Label(
            self.tooltip_window,
            text=self.text,
            justify=tk.LEFT,
            background="#FFFFE0",
            foreground="#000000",
            relief=tk.SOLID,
            borderwidth=1,
            font=("Ubuntu", 10, "normal"),
            padx=8,
            pady=6,
            wraplength=400  # Maximale Breite für Zeilenumbruch
        )
        label.pack()

    def _hide(self):
        """Versteckt Tooltip-Fenster."""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

    def update_text(self, new_text: str):
        """
        Aktualisiert Tooltip-Text.

        Args:
            new_text: Neuer Tooltip-Text
        """
        self.text = new_text
        if self.tooltip_window:
            self._hide()


def create_tooltip(widget: tk.Widget, text: str, delay: int = 500) -> ToolTip:
    """
    Hilfsfunktion zum Erstellen eines Tooltips.

    Args:
        widget: Widget für Tooltip
        text: Tooltip-Text
        delay: Verzögerung in ms

    Returns:
        ToolTip-Instanz
    """
    return ToolTip(widget, text, delay)
