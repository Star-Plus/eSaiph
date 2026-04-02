"""SettingsView — Application settings panel."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import customtkinter as ctk

from ...core.recorder import DEFAULT_SESSIONS_DIR


# Settings file location
SETTINGS_FILE = Path.home() / ".esaiph" / "settings.json"

DEFAULT_SETTINGS = {
    "theme": "dark",
    "default_interval": 1.0,
    "sessions_dir": str(DEFAULT_SESSIONS_DIR),
    "auto_stop_duration": 0,  # 0 = no auto-stop
}


def load_settings() -> dict:
    """Load settings from disk, falling back to defaults."""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            # Merge with defaults
            settings = {**DEFAULT_SETTINGS, **saved}
            return settings
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict):
    """Save settings to disk."""
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)


class SettingsView(ctk.CTkFrame):
    """Settings panel for configuring eSaiph."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._settings = load_settings()

        self.grid_columnconfigure(0, weight=1)

        self._build_ui()

    def _build_ui(self):
        """Build the settings form."""
        # Title
        title = ctk.CTkLabel(
            self,
            text="⚙ Settings",
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        )
        title.grid(row=0, column=0, padx=24, pady=(24, 16), sticky="w")

        # Settings card
        card = ctk.CTkFrame(self, fg_color=("#f0f0f0", "#1a1a2e"), corner_radius=12)
        card.grid(row=1, column=0, padx=24, pady=(0, 16), sticky="ew")
        card.grid_columnconfigure(1, weight=1)

        row = 0

        # ── Theme ──
        ctk.CTkLabel(
            card, text="Theme", font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=row, column=0, padx=16, pady=(16, 8), sticky="w")

        self._theme_var = ctk.StringVar(value=self._settings.get("theme", "dark"))
        theme_menu = ctk.CTkSegmentedButton(
            card,
            values=["Dark", "Light", "System"],
            command=self._on_theme_change,
            font=ctk.CTkFont(size=12),
        )
        theme_menu.set(self._settings.get("theme", "dark").capitalize())
        theme_menu.grid(row=row, column=1, padx=16, pady=(16, 8), sticky="e")
        row += 1

        # Separator
        sep = ctk.CTkFrame(card, height=1, fg_color=("#ddd", "#2a2a3e"))
        sep.grid(row=row, column=0, columnspan=2, padx=16, pady=4, sticky="ew")
        row += 1

        # ── Default Interval ──
        ctk.CTkLabel(
            card, text="Default Sampling Interval", font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=row, column=0, padx=16, pady=8, sticky="w")

        interval_frame = ctk.CTkFrame(card, fg_color="transparent")
        interval_frame.grid(row=row, column=1, padx=16, pady=8, sticky="e")

        self._interval_var = ctk.StringVar(value=str(self._settings.get("default_interval", 1.0)))
        ctk.CTkEntry(
            interval_frame, textvariable=self._interval_var,
            width=80, height=32, corner_radius=8,
            font=ctk.CTkFont(size=13),
        ).grid(row=0, column=0, padx=(0, 4))
        ctk.CTkLabel(interval_frame, text="seconds", font=ctk.CTkFont(size=12)).grid(row=0, column=1)
        row += 1

        # Separator
        sep2 = ctk.CTkFrame(card, height=1, fg_color=("#ddd", "#2a2a3e"))
        sep2.grid(row=row, column=0, columnspan=2, padx=16, pady=4, sticky="ew")
        row += 1

        # ── Auto-stop Duration ──
        ctk.CTkLabel(
            card, text="Auto-Stop Duration", font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=row, column=0, padx=16, pady=8, sticky="w")

        autostop_frame = ctk.CTkFrame(card, fg_color="transparent")
        autostop_frame.grid(row=row, column=1, padx=16, pady=8, sticky="e")

        self._autostop_var = ctk.StringVar(value=str(self._settings.get("auto_stop_duration", 0)))
        ctk.CTkEntry(
            autostop_frame, textvariable=self._autostop_var,
            width=80, height=32, corner_radius=8,
            font=ctk.CTkFont(size=13),
        ).grid(row=0, column=0, padx=(0, 4))
        ctk.CTkLabel(autostop_frame, text="seconds (0 = disabled)", font=ctk.CTkFont(size=12)).grid(row=0, column=1)
        row += 1

        # Separator
        sep3 = ctk.CTkFrame(card, height=1, fg_color=("#ddd", "#2a2a3e"))
        sep3.grid(row=row, column=0, columnspan=2, padx=16, pady=4, sticky="ew")
        row += 1

        # ── Sessions Directory ──
        ctk.CTkLabel(
            card, text="Sessions Directory", font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=row, column=0, padx=16, pady=8, sticky="w")

        self._sessions_dir_var = ctk.StringVar(value=self._settings.get("sessions_dir", str(DEFAULT_SESSIONS_DIR)))
        dir_frame = ctk.CTkFrame(card, fg_color="transparent")
        dir_frame.grid(row=row, column=1, padx=16, pady=8, sticky="e")
        dir_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkEntry(
            dir_frame, textvariable=self._sessions_dir_var,
            width=300, height=32, corner_radius=8,
            font=ctk.CTkFont(size=12),
        ).grid(row=0, column=0, padx=(0, 4))

        ctk.CTkButton(
            dir_frame, text="Browse", width=70, height=32, corner_radius=8,
            fg_color=("#ddd", "#2a2a3e"),
            hover_color=("#ccc", "#3a3a4e"),
            text_color=("#333", "#e0e0e0"),
            font=ctk.CTkFont(size=12),
            command=self._browse_directory,
        ).grid(row=0, column=1)
        row += 1

        # ── Save Button ──
        save_btn = ctk.CTkButton(
            self,
            text="💾 Save Settings",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#00d4aa",
            hover_color="#00b894",
            text_color="#000000",
            height=40,
            corner_radius=10,
            width=180,
            command=self._save,
        )
        save_btn.grid(row=2, column=0, padx=24, pady=16, sticky="w")

        self._status_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#00d4aa",
        )
        self._status_label.grid(row=3, column=0, padx=24, sticky="w")

    def _on_theme_change(self, value: str):
        """Apply theme change immediately."""
        theme = value.lower()
        ctk.set_appearance_mode(theme)
        self._settings["theme"] = theme

    def _browse_directory(self):
        """Open a directory picker."""
        from tkinter import filedialog
        path = filedialog.askdirectory(
            title="Select Sessions Directory",
            initialdir=self._sessions_dir_var.get(),
        )
        if path:
            self._sessions_dir_var.set(path)

    def _save(self):
        """Save all settings to disk."""
        try:
            self._settings["default_interval"] = float(self._interval_var.get())
        except ValueError:
            self._settings["default_interval"] = 1.0

        try:
            self._settings["auto_stop_duration"] = float(self._autostop_var.get())
        except ValueError:
            self._settings["auto_stop_duration"] = 0

        self._settings["sessions_dir"] = self._sessions_dir_var.get()

        save_settings(self._settings)
        self._status_label.configure(text="✓ Settings saved.", text_color="#00d4aa")
        self.after(3000, lambda: self._status_label.configure(text=""))
