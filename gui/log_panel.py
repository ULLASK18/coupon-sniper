"""
Bottom log panel: scrolling color-coded live log output.
"""
from __future__ import annotations

import customtkinter as ctk
from datetime import datetime


class LogPanel(ctk.CTkFrame):
    """Bottom panel showing color-coded live log entries."""

    MAX_LINES = 500

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(fg_color="gray14", corner_radius=12)
        self._line_count = 0
        self._build()

    def _build(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(10, 5))

        ctk.CTkLabel(
            header,
            text="LIVE LOGS",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="gray50",
        ).pack(side="left")

        ctk.CTkButton(
            header,
            text="Clear",
            width=50,
            height=24,
            font=ctk.CTkFont(size=10),
            fg_color="gray25",
            hover_color="gray35",
            command=self.clear,
        ).pack(side="right")

        # Log text area
        self.log_text = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="gray10",
            corner_radius=8,
            wrap="word",
            state="disabled",
            height=160,
        )
        self.log_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Configure text tags for colors
        self.log_text._textbox.tag_configure("time", foreground="#6b7280")
        self.log_text._textbox.tag_configure("info", foreground="#d1d5db")
        self.log_text._textbox.tag_configure("coupon", foreground="#10b981")
        self.log_text._textbox.tag_configure("error", foreground="#ef4444")
        self.log_text._textbox.tag_configure("warning", foreground="#f59e0b")
        self.log_text._textbox.tag_configure("debug", foreground="#6b7280")

    def add_log(self, level: str, message: str) -> None:
        """Add a new log entry with color coding."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        level_upper = level.upper()

        tag = "info"
        if level_upper in ("COUPON", "SUCCESS"):
            tag = "coupon"
        elif level_upper == "ERROR":
            tag = "error"
        elif level_upper == "WARNING":
            tag = "warning"
        elif level_upper == "DEBUG":
            tag = "debug"

        self.log_text.configure(state="normal")

        # Trim if too many lines
        self._line_count += 1
        if self._line_count > self.MAX_LINES:
            self.log_text._textbox.delete("1.0", "2.0")
            self._line_count -= 1

        self.log_text._textbox.insert("end", f"  {timestamp}  ", "time")
        self.log_text._textbox.insert("end", f"{message}\n", tag)

        self.log_text.configure(state="disabled")
        self.log_text._textbox.see("end")

    def clear(self) -> None:
        """Clear all log entries."""
        self.log_text.configure(state="normal")
        self.log_text._textbox.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        self._line_count = 0
