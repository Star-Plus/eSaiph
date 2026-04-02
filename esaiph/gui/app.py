"""eSaiph GUI — Main application window with sidebar navigation."""

from __future__ import annotations

import customtkinter as ctk

from .views.record_view import RecordView
from .views.logs_view import LogsView
from .views.settings_view import SettingsView


class ESaiphApp(ctk.CTk):
    """Main eSaiph GUI application.

    Features a sidebar with navigation buttons and a content area
    that swaps between Record, Logs, and Settings views.
    """

    def __init__(self):
        super().__init__()

        # ── Window Configuration ──
        self.title("eSaiph — Software Testing & Monitoring")
        self.geometry("1200x750")
        self.minsize(900, 600)

        # Theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        # ── Layout ──
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_content_area()

        # Show default view
        self._show_view("record")

    def _build_sidebar(self):
        """Build the left sidebar with navigation buttons."""
        sidebar = ctk.CTkFrame(
            self,
            width=200,
            corner_radius=0,
            fg_color=("#e8e8f0", "#0d0d1a"),
        )
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_rowconfigure(5, weight=1)  # Spacer
        sidebar.grid_propagate(False)

        # Logo / Title
        logo_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=16, pady=(24, 32), sticky="ew")

        ctk.CTkLabel(
            logo_frame,
            text="eSaiph",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color="#00d4aa",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            logo_frame,
            text="Software Testing Tool",
            font=ctk.CTkFont(size=11),
            text_color=("#888", "#666"),
        ).grid(row=1, column=0, sticky="w")

        # Navigation buttons
        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        nav_items = [
            ("record", "🔴  Record", 1),
            ("logs", "📋  Logs", 2),
            ("settings", "⚙  Settings", 3),
        ]

        for key, text, row in nav_items:
            btn = ctk.CTkButton(
                sidebar,
                text=text,
                font=ctk.CTkFont(size=14),
                fg_color="transparent",
                hover_color=("#d0d0e0", "#1a1a2e"),
                text_color=("#333", "#c0c0c0"),
                anchor="w",
                height=42,
                corner_radius=8,
                command=lambda k=key: self._show_view(k),
            )
            btn.grid(row=row, column=0, padx=12, pady=2, sticky="ew")
            self._nav_buttons[key] = btn

        # Version label at bottom
        ctk.CTkLabel(
            sidebar,
            text="v0.1.0",
            font=ctk.CTkFont(size=10),
            text_color=("#bbb", "#444"),
        ).grid(row=6, column=0, padx=16, pady=(0, 16), sticky="s")

    def _build_content_area(self):
        """Build the main content area where views are displayed."""
        self._content = ctk.CTkFrame(
            self,
            fg_color=("#ffffff", "#121220"),
            corner_radius=0,
        )
        self._content.grid(row=0, column=1, sticky="nsew")
        self._content.grid_columnconfigure(0, weight=1)
        self._content.grid_rowconfigure(0, weight=1)

        # Pre-create views
        self._views: dict[str, ctk.CTkFrame] = {}
        self._current_view: str | None = None

    def _show_view(self, view_name: str):
        """Switch to a specific view."""
        # Update nav button styles
        for key, btn in self._nav_buttons.items():
            if key == view_name:
                btn.configure(
                    fg_color=("#d0d0e0", "#1a1a2e"),
                    text_color=("#000", "#00d4aa"),
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=("#333", "#c0c0c0"),
                )

        # Hide current view
        if self._current_view and self._current_view in self._views:
            self._views[self._current_view].grid_forget()

        # Create view if not exists
        if view_name not in self._views:
            if view_name == "record":
                self._views[view_name] = RecordView(self._content)
            elif view_name == "logs":
                self._views[view_name] = LogsView(self._content)
            elif view_name == "settings":
                self._views[view_name] = SettingsView(self._content)

        # Show view
        self._views[view_name].grid(row=0, column=0, sticky="nsew")
        self._current_view = view_name

        # Refresh logs view when switching to it
        if view_name == "logs" and hasattr(self._views[view_name], "_refresh_sessions"):
            self._views[view_name]._refresh_sessions()

    def on_closing(self):
        """Handle window close — stop any active recordings."""
        if "record" in self._views:
            record_view = self._views["record"]
            if hasattr(record_view, "_session") and record_view._session and record_view._session.is_running:
                record_view._session.stop("gui_closed")
        self.destroy()


def launch_gui():
    """Launch the eSaiph GUI application."""
    app = ESaiphApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
