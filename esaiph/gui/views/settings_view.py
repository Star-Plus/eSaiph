"""SettingsView — Cosmic-styled app settings."""

from __future__ import annotations

import json
from pathlib import Path

import customtkinter as ctk

from ..theme import (
    BG_BASE, BG_CARD, BG_INPUT,
    BORDER, BORDER_LIGHT,
    TEXT_MAIN, TEXT_MUTED, TEXT_DIM,
    PINK, PINK_HOVER,
    FONT_BODY, FONT_HEADING,
    RADIUS_SM, RADIUS_LG,
)
from ...core.recorder import DEFAULT_SESSIONS_DIR

SETTINGS_FILE = Path.home() / ".esaiph" / "settings.json"
DEFAULT_SETTINGS = {
    "theme": "dark",
    "default_interval": 1.0,
    "sessions_dir": str(DEFAULT_SESSIONS_DIR),
    "auto_stop_duration": 0,
}


def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return {**DEFAULT_SETTINGS, **json.load(f)}
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()


def save_settings(s: dict):
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=2)


class SettingsView(ctk.CTkFrame):
    """Settings panel with cosmic styling."""

    def __init__(self, master, on_theme_change=None, **kwargs):
        super().__init__(master, fg_color=BG_BASE, corner_radius=0, **kwargs)
        self._settings = load_settings()
        self._on_theme_change = on_theme_change
        self.grid_columnconfigure(0, weight=1)
        self._build_header()
        self._build_form()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=28, pady=(24, 0), sticky="ew")

        t = ctk.CTkFrame(header, fg_color="transparent")
        t.grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            t, text="App ",
            font=ctk.CTkFont(family=FONT_HEADING, size=24),
            text_color=TEXT_MAIN, anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            t, text="Settings",
            font=ctk.CTkFont(family=FONT_HEADING, size=24, weight="bold"),
            text_color=TEXT_MAIN, anchor="w",
        ).grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(
            header,
            text="Configure recording defaults and preferences.",
            font=ctk.CTkFont(family=FONT_BODY, size=12),
            text_color=TEXT_MUTED, anchor="w",
        ).grid(row=1, column=0, pady=(2, 0), sticky="w")

    def _build_form(self):
        card = ctk.CTkFrame(
            self, fg_color=BG_CARD,
            corner_radius=RADIUS_LG,
            border_width=1, border_color=BORDER,
        )
        card.grid(row=1, column=0, padx=28, pady=(16, 20), sticky="ew")
        card.grid_columnconfigure(1, weight=1)

        row = 0

        # Theme
        row = self._add_row(card, row, "Theme")
        seg = ctk.CTkSegmentedButton(
            card, values=["Dark", "Light", "System"],
            command=self._on_theme_toggle,
            font=ctk.CTkFont(family=FONT_BODY, size=11),
            fg_color=BG_INPUT,
            selected_color=PINK,
            selected_hover_color=PINK_HOVER,
            unselected_color=BG_INPUT,
            unselected_hover_color=BORDER_LIGHT,
            text_color=TEXT_MAIN,
            corner_radius=RADIUS_SM,
        )
        seg.set(self._settings.get("theme", "dark").capitalize())
        seg.grid(row=row - 1, column=1, padx=18, pady=12, sticky="e")
        self._sep(card, row); row += 1

        # Interval
        row = self._add_row(card, row, "Default Sampling Interval")
        f = ctk.CTkFrame(card, fg_color="transparent")
        f.grid(row=row - 1, column=1, padx=18, pady=12, sticky="e")
        self._interval_var = ctk.StringVar(value=str(self._settings.get("default_interval", 1.0)))
        ctk.CTkEntry(
            f, textvariable=self._interval_var, width=60, height=30,
            corner_radius=RADIUS_SM, fg_color=BG_INPUT,
            border_width=1, border_color=BORDER,
            text_color=TEXT_MAIN, font=ctk.CTkFont(family=FONT_BODY, size=12),
            justify="center",
        ).grid(row=0, column=0, padx=(0, 6))
        ctk.CTkLabel(f, text="seconds", font=ctk.CTkFont(family=FONT_BODY, size=11), text_color=TEXT_DIM).grid(row=0, column=1)
        self._sep(card, row); row += 1

        # Auto-stop
        row = self._add_row(card, row, "Auto-Stop Duration")
        f2 = ctk.CTkFrame(card, fg_color="transparent")
        f2.grid(row=row - 1, column=1, padx=18, pady=12, sticky="e")
        self._autostop_var = ctk.StringVar(value=str(self._settings.get("auto_stop_duration", 0)))
        ctk.CTkEntry(
            f2, textvariable=self._autostop_var, width=60, height=30,
            corner_radius=RADIUS_SM, fg_color=BG_INPUT,
            border_width=1, border_color=BORDER,
            text_color=TEXT_MAIN, font=ctk.CTkFont(family=FONT_BODY, size=12),
            justify="center",
        ).grid(row=0, column=0, padx=(0, 6))
        ctk.CTkLabel(f2, text="s (0 = off)", font=ctk.CTkFont(family=FONT_BODY, size=11), text_color=TEXT_DIM).grid(row=0, column=1)
        self._sep(card, row); row += 1

        # Sessions dir
        row = self._add_row(card, row, "Sessions Directory")
        f3 = ctk.CTkFrame(card, fg_color="transparent")
        f3.grid(row=row - 1, column=1, padx=18, pady=12, sticky="e")
        self._dir_var = ctk.StringVar(value=self._settings.get("sessions_dir", str(DEFAULT_SESSIONS_DIR)))
        ctk.CTkEntry(
            f3, textvariable=self._dir_var, width=260, height=30,
            corner_radius=RADIUS_SM, fg_color=BG_INPUT,
            border_width=1, border_color=BORDER,
            text_color=TEXT_MAIN, font=ctk.CTkFont(family=FONT_BODY, size=11),
        ).grid(row=0, column=0, padx=(0, 6))
        ctk.CTkButton(
            f3, text="Browse", width=60, height=30,
            corner_radius=RADIUS_SM,
            fg_color=BG_INPUT, hover_color=BG_BASE,
            text_color=TEXT_MUTED, border_width=1, border_color=BORDER,
            font=ctk.CTkFont(family=FONT_BODY, size=11),
            command=self._browse,
        ).grid(row=0, column=1)

        # Save
        save_frame = ctk.CTkFrame(self, fg_color="transparent")
        save_frame.grid(row=2, column=0, padx=28, pady=(0, 16), sticky="w")

        ctk.CTkButton(
            save_frame, text="Save Settings",
            font=ctk.CTkFont(family=FONT_BODY, size=13, weight="bold"),
            fg_color=PINK, hover_color=PINK_HOVER, text_color="#ffffff",
            height=36, corner_radius=RADIUS_SM, width=140,
            command=self._save,
        ).grid(row=0, column=0)

        self._status_lbl = ctk.CTkLabel(
            save_frame, text="",
            font=ctk.CTkFont(family=FONT_BODY, size=11), text_color=PINK,
        )
        self._status_lbl.grid(row=0, column=1, padx=(12, 0))

    def _add_row(self, parent, row, label):
        ctk.CTkLabel(
            parent, text=label,
            font=ctk.CTkFont(family=FONT_BODY, size=13, weight="bold"),
            text_color=TEXT_MAIN, anchor="w",
        ).grid(row=row, column=0, padx=18, pady=12, sticky="w")
        return row + 1

    def _sep(self, parent, row):
        ctk.CTkFrame(parent, height=1, fg_color=BORDER).grid(
            row=row, column=0, columnspan=2, padx=18, sticky="ew",
        )

    def _on_theme_toggle(self, value):
        theme = value.lower()
        ctk.set_appearance_mode(theme)
        self._settings["theme"] = theme
        if self._on_theme_change:
            self._on_theme_change(theme)

    def _browse(self):
        from tkinter import filedialog
        p = filedialog.askdirectory(initialdir=self._dir_var.get())
        if p:
            self._dir_var.set(p)

    def _save(self):
        try: self._settings["default_interval"] = float(self._interval_var.get())
        except ValueError: self._settings["default_interval"] = 1.0
        try: self._settings["auto_stop_duration"] = float(self._autostop_var.get())
        except ValueError: self._settings["auto_stop_duration"] = 0
        self._settings["sessions_dir"] = self._dir_var.get()
        save_settings(self._settings)
        self._status_lbl.configure(text="Saved ✓", text_color=PINK)
        self.after(3000, lambda: self._status_lbl.configure(text=""))
