"""eSaiph GUI — Cosmic Dashboard main application."""

from __future__ import annotations

import customtkinter as ctk

from .theme import (
    BG_BASE, BG_CARD, BG_NAVBAR, BG_ELEVATED,
    BORDER, BORDER_LIGHT,
    TEXT_MAIN, TEXT_MUTED, TEXT_DIM,
    PINK, PINK_HOVER, PURPLE,
    FONT_BODY, FONT_HEADING,
    RADIUS_SM,
)
from .views.record_view import RecordView
from .views.logs_view import LogsView
from .views.settings_view import SettingsView


class ESaiphApp(ctk.CTk):
    """Main application with cosmic dark dashboard aesthetic."""

    def __init__(self):
        super().__init__()

        self.title("eSaiph")
        self.geometry("1360x820")
        self.minsize(1000, 650)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.configure(fg_color=BG_BASE)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_content_area()
        self._show_view("record")

    def _build_sidebar(self):
        """Deep navy sidebar with pink accent active state."""
        sidebar = ctk.CTkFrame(
            self, width=200, corner_radius=0,
            fg_color=BG_NAVBAR, border_width=0,
        )
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_rowconfigure(4, weight=1)
        sidebar.grid_propagate(False)

        # Brand
        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.grid(row=0, column=0, padx=18, pady=(26, 32), sticky="ew")

        ctk.CTkLabel(
            brand, text="eSaiph",
            font=ctk.CTkFont(family=FONT_HEADING, size=22, weight="bold"),
            text_color=PINK,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            brand, text="Software Testing Tool",
            font=ctk.CTkFont(family=FONT_BODY, size=10),
            text_color=TEXT_DIM,
        ).grid(row=1, column=0, sticky="w")

        # Separator
        ctk.CTkFrame(sidebar, height=1, fg_color=BORDER).grid(
            row=1, column=0, padx=14, sticky="ew",
        )

        # Navigation — each has a left accent bar when active
        nav = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav.grid(row=2, column=0, padx=10, pady=(18, 0), sticky="ew")
        nav.grid_columnconfigure(0, weight=1)

        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        self._nav_accents: dict[str, ctk.CTkFrame] = {}

        for i, (key, label) in enumerate([
            ("record",   "⦿  Dashboard"),
            ("logs",     "☰  Logs"),
            ("settings", "⚙  Settings"),
        ]):
            row_frame = ctk.CTkFrame(nav, fg_color="transparent")
            row_frame.grid(row=i, column=0, pady=1, sticky="ew")
            row_frame.grid_columnconfigure(1, weight=1)

            # Left accent bar (hidden by default)
            accent = ctk.CTkFrame(
                row_frame, width=3, corner_radius=2,
                fg_color="transparent",
            )
            accent.grid(row=0, column=0, sticky="ns", padx=(0, 2), pady=4)
            self._nav_accents[key] = accent

            btn = ctk.CTkButton(
                row_frame,
                text=f"  {label}",
                font=ctk.CTkFont(family=FONT_BODY, size=13),
                fg_color="transparent",
                hover_color=("#E0DEE8", "#151424"),
                text_color=TEXT_MUTED,
                anchor="w",
                height=38,
                corner_radius=RADIUS_SM,
                command=lambda k=key: self._show_view(k),
            )
            btn.grid(row=0, column=1, sticky="ew")
            self._nav_buttons[key] = btn

        # Version
        ver = ctk.CTkFrame(sidebar, fg_color="transparent")
        ver.grid(row=5, column=0, padx=18, pady=(0, 14), sticky="sew")
        ctk.CTkFrame(ver, height=1, fg_color=BORDER).grid(row=0, column=0, pady=(0, 10), sticky="ew")
        ctk.CTkLabel(
            ver, text="v0.1.0",
            font=ctk.CTkFont(family=FONT_BODY, size=9),
            text_color=TEXT_DIM,
        ).grid(row=1, column=0, sticky="w")

    def _build_content_area(self):
        # Border edge
        ctk.CTkFrame(self, width=1, fg_color=BORDER, corner_radius=0).grid(
            row=0, column=0, sticky="nse",
        )

        self._content = ctk.CTkFrame(self, fg_color=BG_BASE, corner_radius=0)
        self._content.grid(row=0, column=1, sticky="nsew")
        self._content.grid_columnconfigure(0, weight=1)
        self._content.grid_rowconfigure(0, weight=1)

        self._views: dict[str, ctk.CTkFrame] = {}
        self._current_view: str | None = None

    def _show_view(self, view_name: str):
        # Nav styling: pink accent bar + bold text for active
        for key, btn in self._nav_buttons.items():
            accent = self._nav_accents[key]
            if key == view_name:
                btn.configure(
                    fg_color=("#E0DEE8", "#151424"),
                    text_color=TEXT_MAIN,
                    font=ctk.CTkFont(family=FONT_BODY, size=13, weight="bold"),
                )
                accent.configure(fg_color=PINK)
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=TEXT_MUTED,
                    font=ctk.CTkFont(family=FONT_BODY, size=13),
                )
                accent.configure(fg_color="transparent")

        if self._current_view and self._current_view in self._views:
            self._views[self._current_view].grid_forget()

        if view_name not in self._views:
            if view_name == "record":
                self._views[view_name] = RecordView(self._content)
            elif view_name == "logs":
                self._views[view_name] = LogsView(self._content)
            elif view_name == "settings":
                self._views[view_name] = SettingsView(
                    self._content, on_theme_change=self._handle_theme_change,
                )

        self._views[view_name].grid(row=0, column=0, sticky="nsew")
        self._current_view = view_name

        if view_name == "logs" and hasattr(self._views[view_name], "_refresh_sessions"):
            self._views[view_name]._refresh_sessions()

    def _handle_theme_change(self, theme: str):
        self.after(100, self._refresh_canvases)

    def _refresh_canvases(self):
        if "record" in self._views:
            rv = self._views["record"]
            if hasattr(rv, "refresh_theme"):
                rv.refresh_theme()

    def on_closing(self):
        if "record" in self._views:
            rv = self._views["record"]
            if hasattr(rv, "_session") and rv._session and rv._session.is_running:
                rv._session.stop("gui_closed")
        self.destroy()


def launch_gui():
    app = ESaiphApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
