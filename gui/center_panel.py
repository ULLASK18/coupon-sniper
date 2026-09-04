"""
Center panel: live status cards, latest coupon highlight, statistics.
"""
from __future__ import annotations

import customtkinter as ctk
from datetime import datetime


class CenterPanel(ctk.CTkFrame):
    """Center panel showing live monitoring status, stats, and latest coupon."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(fg_color="transparent")
        self._build()

    def _build(self) -> None:
        # ── Status Header ──
        header = ctk.CTkFrame(self, fg_color="gray14", corner_radius=12)
        header.pack(fill="x", padx=5, pady=(0, 10))

        ctk.CTkLabel(
            header,
            text="LIVE STATUS",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="gray50",
        ).pack(padx=15, pady=(12, 5), anchor="w")

        # Stats grid
        stats_grid = ctk.CTkFrame(header, fg_color="transparent")
        stats_grid.pack(fill="x", padx=10, pady=(0, 15))
        stats_grid.columnconfigure((0, 1, 2, 3), weight=1)

        self.stat_monitoring = self._make_stat_card(stats_grid, "Monitoring", "0", 0, 0)
        self.stat_workers = self._make_stat_card(stats_grid, "Workers", "0", 0, 1)
        self.stat_today = self._make_stat_card(stats_grid, "Today", "0", 0, 2)
        self.stat_total = self._make_stat_card(stats_grid, "All Time", "0", 0, 3)

        # ── Latest Coupon Highlight ──
        self.coupon_frame = ctk.CTkFrame(self, corner_radius=12)
        self.coupon_frame.configure(fg_color="gray14")
        self.coupon_frame.pack(fill="x", padx=5, pady=5)

        inner = ctk.CTkFrame(self.coupon_frame, fg_color="transparent")
        inner.pack(fill="x", padx=15, pady=15)

        top_row = ctk.CTkFrame(inner, fg_color="transparent")
        top_row.pack(fill="x")

        ctk.CTkLabel(
            top_row,
            text="LATEST COUPON",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="gray50",
        ).pack(side="left")

        self.coupon_time_label = ctk.CTkLabel(
            top_row,
            text="--:--:--",
            font=ctk.CTkFont(size=11),
            text_color="gray50",
        )
        self.coupon_time_label.pack(side="right")

        self.coupon_code_label = ctk.CTkLabel(
            inner,
            text="Waiting for coupons...",
            font=ctk.CTkFont(family="Consolas", size=28, weight="bold"),
            text_color="gray40",
        )
        self.coupon_code_label.pack(pady=(10, 5))

        self.coupon_source_label = ctk.CTkLabel(
            inner,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="gray50",
        )
        self.coupon_source_label.pack()

        self.copy_btn = ctk.CTkButton(
            inner,
            text="📋 Copy to Clipboard",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#3b82f6",
            hover_color="#2563eb",
            height=34,
            state="disabled",
            command=self._copy_latest,
        )
        self.copy_btn.pack(pady=(10, 0))

        self._latest_code = ""

        # ── Last Poll & Clipboard Status ──
        info_frame = ctk.CTkFrame(self, fg_color="gray14", corner_radius=12)
        info_frame.pack(fill="x", padx=5, pady=5)

        info_inner = ctk.CTkFrame(info_frame, fg_color="transparent")
        info_inner.pack(fill="x", padx=15, pady=12)
        info_inner.columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(
            info_inner, text="Last Poll", font=ctk.CTkFont(size=11),
            text_color="gray50",
        ).grid(row=0, column=0, sticky="w")
        self.last_poll_label = ctk.CTkLabel(
            info_inner, text="—", font=ctk.CTkFont(size=11),
            text_color="gray70",
        )
        self.last_poll_label.grid(row=0, column=1, sticky="e")

        ctk.CTkLabel(
            info_inner, text="Clipboard", font=ctk.CTkFont(size=11),
            text_color="gray50",
        ).grid(row=1, column=0, sticky="w", pady=(5, 0))
        self.clipboard_label = ctk.CTkLabel(
            info_inner, text="Empty", font=ctk.CTkFont(size=11),
            text_color="gray70",
        )
        self.clipboard_label.grid(row=1, column=1, sticky="e", pady=(5, 0))

        ctk.CTkLabel(
            info_inner, text="Status", font=ctk.CTkFont(size=11),
            text_color="gray50",
        ).grid(row=2, column=0, sticky="w", pady=(5, 0))
        self.status_label = ctk.CTkLabel(
            info_inner, text="Idle", font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#f59e0b",
        )
        self.status_label.grid(row=2, column=1, sticky="e", pady=(5, 0))

    def _make_stat_card(self, parent, title: str, value: str, row: int, col: int) -> ctk.CTkLabel:
        """Create a stat card inside the grid."""
        frame = ctk.CTkFrame(parent, fg_color="gray18", corner_radius=10)
        frame.grid(row=row, column=col, padx=3, pady=3, sticky="nsew")

        ctk.CTkLabel(
            frame, text=title,
            font=ctk.CTkFont(size=10),
            text_color="gray50",
        ).pack(padx=10, pady=(8, 0))

        val_label = ctk.CTkLabel(
            frame, text=value,
            font=ctk.CTkFont(family="Consolas", size=22, weight="bold"),
            text_color="#06b6d4",
        )
        val_label.pack(padx=10, pady=(0, 8))
        return val_label

    # ── Public update methods ──────────────────────────────────────

    def set_latest_coupon(self, code: str, account: str = "") -> None:
        """Highlight a newly detected coupon."""
        self._latest_code = code
        self.coupon_code_label.configure(text=code, text_color="#10b981")
        self.coupon_time_label.configure(text=datetime.now().strftime("%H:%M:%S"))
        self.coupon_source_label.configure(
            text=f"from @{account}" if account else "",
            text_color="gray60",
        )
        self.copy_btn.configure(state="normal")
        self.clipboard_label.configure(text=code, text_color="#10b981")

        # Flash the frame
        self.coupon_frame.configure(fg_color="#064e3b")
        self.after(1500, lambda: self.coupon_frame.configure(fg_color="gray14"))

    def update_stats(
        self,
        monitoring: int = 0,
        workers: int = 0,
        today: int = 0,
        total: int = 0,
    ) -> None:
        self.stat_monitoring.configure(text=str(monitoring))
        self.stat_workers.configure(text=str(workers))
        self.stat_today.configure(text=str(today))
        self.stat_total.configure(text=str(total))

    def set_monitoring_status(self, running: bool) -> None:
        if running:
            self.status_label.configure(text="Monitoring", text_color="#10b981")
        else:
            self.status_label.configure(text="Idle", text_color="#f59e0b")

    def update_last_poll(self) -> None:
        self.last_poll_label.configure(
            text=datetime.now().strftime("%H:%M:%S")
        )

    def _copy_latest(self) -> None:
        if self._latest_code:
            try:
                import pyperclip
                pyperclip.copy(self._latest_code)
                self.copy_btn.configure(text="✓ Copied!", fg_color="#10b981")
                self.after(
                    2000,
                    lambda: self.copy_btn.configure(
                        text="📋 Copy to Clipboard", fg_color="#3b82f6"
                    ),
                )
            except Exception:
                pass
