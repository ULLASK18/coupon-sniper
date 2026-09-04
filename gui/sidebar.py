"""
Left sidebar panel: account list, monitoring controls.
"""
from __future__ import annotations

import customtkinter as ctk
from typing import Callable, Optional


class Sidebar(ctk.CTkFrame):
    """Left panel with account management and monitoring controls."""

    def __init__(
        self,
        master,
        on_start: Optional[Callable] = None,
        on_stop: Optional[Callable] = None,
        on_add_account: Optional[Callable[[str], None]] = None,
        on_remove_account: Optional[Callable[[str], None]] = None,
        on_toggle_account: Optional[Callable[[str, bool], None]] = None,
        on_open_settings: Optional[Callable] = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)

        self._on_start = on_start
        self._on_stop = on_stop
        self._on_add_account = on_add_account
        self._on_remove_account = on_remove_account
        self._on_toggle_account = on_toggle_account
        self._on_open_settings = on_open_settings

        self._account_widgets: dict[str, dict] = {}
        self.configure(fg_color="transparent")

        self._build()

    def _build(self) -> None:
        # ── Title ──
        title = ctk.CTkLabel(
            self,
            text="🎯 Coupon Sniper",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        title.pack(pady=(10, 5), padx=15, anchor="w")

        subtitle = ctk.CTkLabel(
            self,
            text="Real-time coupon monitoring",
            font=ctk.CTkFont(size=12),
            text_color="gray60",
        )
        subtitle.pack(padx=15, anchor="w")

        # ── Monitoring Controls ──
        controls_frame = ctk.CTkFrame(self, fg_color="gray14", corner_radius=12)
        controls_frame.pack(fill="x", padx=10, pady=(20, 10))

        ctk.CTkLabel(
            controls_frame,
            text="MONITORING",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="gray50",
        ).pack(padx=15, pady=(12, 5), anchor="w")

        btn_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(0, 12))

        self.start_btn = ctk.CTkButton(
            btn_frame,
            text="▶  Start",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            height=38,
            command=self._on_start_click,
        )
        self.start_btn.pack(side="left", expand=True, fill="x", padx=(0, 4))

        self.stop_btn = ctk.CTkButton(
            btn_frame,
            text="■  Stop",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#ef4444",
            hover_color="#dc2626",
            height=38,
            state="disabled",
            command=self._on_stop_click,
        )
        self.stop_btn.pack(side="right", expand=True, fill="x", padx=(4, 0))

        # ── Account List ──
        acct_frame = ctk.CTkFrame(self, fg_color="gray14", corner_radius=12)
        acct_frame.pack(fill="both", expand=True, padx=10, pady=5)

        header_frame = ctk.CTkFrame(acct_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=(12, 5))

        ctk.CTkLabel(
            header_frame,
            text="ACCOUNTS",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="gray50",
        ).pack(side="left")

        self.account_count_label = ctk.CTkLabel(
            header_frame,
            text="0",
            font=ctk.CTkFont(size=11),
            text_color="gray60",
        )
        self.account_count_label.pack(side="right")

        # Scrollable account list
        self.account_list = ctk.CTkScrollableFrame(
            acct_frame,
            fg_color="transparent",
            scrollbar_button_color="gray25",
        )
        self.account_list.pack(fill="both", expand=True, padx=5, pady=5)

        # Add account input
        add_frame = ctk.CTkFrame(acct_frame, fg_color="transparent")
        add_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.account_input = ctk.CTkEntry(
            add_frame,
            placeholder_text="@username",
            height=34,
            font=ctk.CTkFont(size=12),
        )
        self.account_input.pack(side="left", expand=True, fill="x", padx=(5, 4))
        self.account_input.bind("<Return>", lambda e: self._on_add_click())

        ctk.CTkButton(
            add_frame,
            text="+",
            width=34,
            height=34,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#3b82f6",
            hover_color="#2563eb",
            command=self._on_add_click,
        ).pack(side="right", padx=(0, 5))

        # ── Settings Button ──
        ctk.CTkButton(
            self,
            text="⚙  Settings",
            font=ctk.CTkFont(size=13),
            fg_color="gray20",
            hover_color="gray30",
            height=36,
            command=self._on_open_settings,
        ).pack(fill="x", padx=10, pady=(5, 15))

    def _on_start_click(self) -> None:
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        if self._on_start:
            self._on_start()

    def _on_stop_click(self) -> None:
        self.stop_btn.configure(state="disabled")
        self.start_btn.configure(state="normal")
        if self._on_stop:
            self._on_stop()

    def _on_add_click(self) -> None:
        username = self.account_input.get().strip()
        if username and self._on_add_account:
            self._on_add_account(username)
            self.account_input.delete(0, "end")

    def add_account_widget(self, username: str, enabled: bool = True) -> None:
        """Add an account row to the list."""
        username = username.lstrip("@").lower()
        if username in self._account_widgets:
            return

        row = ctk.CTkFrame(self.account_list, fg_color="gray18", corner_radius=8, height=36)
        row.pack(fill="x", pady=2, padx=2)
        row.pack_propagate(False)

        # Status indicator dot
        status_dot = ctk.CTkLabel(
            row, text="●", font=ctk.CTkFont(size=10),
            text_color="#10b981" if enabled else "gray50",
            width=20,
        )
        status_dot.pack(side="left", padx=(10, 2))

        # Username label
        label = ctk.CTkLabel(
            row,
            text=f"@{username}",
            font=ctk.CTkFont(size=12),
            anchor="w",
        )
        label.pack(side="left", padx=5, expand=True, fill="x")

        # Status text
        status_label = ctk.CTkLabel(
            row,
            text="idle",
            font=ctk.CTkFont(size=10),
            text_color="gray50",
            width=60,
        )
        status_label.pack(side="left", padx=2)

        # Enable/Disable switch
        switch_var = ctk.BooleanVar(value=enabled)
        switch = ctk.CTkSwitch(
            row,
            text="",
            variable=switch_var,
            width=40,
            onvalue=True,
            offvalue=False,
            command=lambda: self._on_toggle(username, switch_var.get()),
            switch_width=36,
            switch_height=18,
        )
        switch.pack(side="left", padx=2)

        # Remove button
        remove_btn = ctk.CTkButton(
            row,
            text="✕",
            width=28,
            height=28,
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            hover_color="gray30",
            text_color="gray50",
            command=lambda: self._on_remove(username),
        )
        remove_btn.pack(side="right", padx=(0, 5))

        self._account_widgets[username] = {
            "row": row,
            "label": label,
            "status_dot": status_dot,
            "status_label": status_label,
            "switch_var": switch_var,
        }
        self.account_count_label.configure(text=str(len(self._account_widgets)))

    def remove_account_widget(self, username: str) -> None:
        """Remove an account row from the list."""
        username = username.lstrip("@").lower()
        if username in self._account_widgets:
            self._account_widgets[username]["row"].destroy()
            del self._account_widgets[username]
            self.account_count_label.configure(text=str(len(self._account_widgets)))

    def update_account_status(self, username: str, status: str, detail: str = "") -> None:
        """Update the status indicator for an account."""
        username = username.lstrip("@").lower()
        if username not in self._account_widgets:
            return
        w = self._account_widgets[username]

        colors = {
            "monitoring": "#10b981",
            "starting": "#f59e0b",
            "error": "#ef4444",
            "crashed": "#ef4444",
            "stopped": "gray50",
            "idle": "gray50",
            "waiting": "#f59e0b",
        }
        color = colors.get(status, "gray50")
        w["status_dot"].configure(text_color=color)
        w["status_label"].configure(text=status, text_color=color)

    def set_monitoring_state(self, running: bool) -> None:
        """Update button states based on monitoring status."""
        if running:
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
        else:
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")

    def _on_toggle(self, username: str, enabled: bool) -> None:
        if self._on_toggle_account:
            self._on_toggle_account(username, enabled)

    def _on_remove(self, username: str) -> None:
        if self._on_remove_account:
            self._on_remove_account(username)
