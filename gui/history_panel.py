"""
Right panel: coupon history table with search, copy, and CSV export.
"""
from __future__ import annotations

import customtkinter as ctk
from typing import Callable, Optional
from database.db import Coupon


class HistoryPanel(ctk.CTkFrame):
    """Right panel showing coupon detection history with search and export."""

    def __init__(
        self,
        master,
        on_export_csv: Optional[Callable] = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.configure(fg_color="transparent")
        self._on_export_csv = on_export_csv
        self._coupon_rows: list[ctk.CTkFrame] = []
        self._build()

    def _build(self) -> None:
        container = ctk.CTkFrame(self, fg_color="gray14", corner_radius=12)
        container.pack(fill="both", expand=True, padx=5, pady=0)

        # Header
        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(12, 5))

        ctk.CTkLabel(
            header,
            text="COUPON HISTORY",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="gray50",
        ).pack(side="left")

        ctk.CTkButton(
            header,
            text="📥 Export CSV",
            width=90,
            height=26,
            font=ctk.CTkFont(size=10),
            fg_color="gray25",
            hover_color="gray35",
            command=self._on_export_csv,
        ).pack(side="right")

        # Search
        self.search_input = ctk.CTkEntry(
            container,
            placeholder_text="🔍  Search coupons...",
            height=32,
            font=ctk.CTkFont(size=12),
        )
        self.search_input.pack(fill="x", padx=15, pady=(5, 10))
        self.search_input.bind("<KeyRelease>", lambda e: self._on_search())

        # Column headers
        col_header = ctk.CTkFrame(container, fg_color="gray18", corner_radius=6, height=28)
        col_header.pack(fill="x", padx=10, pady=(0, 2))
        col_header.pack_propagate(False)

        for text, w in [("Time", 70), ("Account", 80), ("Code", 120), ("Status", 50)]:
            ctk.CTkLabel(
                col_header,
                text=text,
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color="gray50",
                width=w,
            ).pack(side="left", padx=5)

        # Scrollable list
        self.history_list = ctk.CTkScrollableFrame(
            container,
            fg_color="transparent",
            scrollbar_button_color="gray25",
        )
        self.history_list.pack(fill="both", expand=True, padx=5, pady=(0, 10))

    def load_history(self, coupons: list[Coupon]) -> None:
        """Populate the history list from database records."""
        # Clear existing
        for row in self._coupon_rows:
            row.destroy()
        self._coupon_rows.clear()

        for coupon in coupons:
            self._add_coupon_row(coupon)

    def add_coupon(self, coupon: Coupon) -> None:
        """Add a single new coupon to the top of the list."""
        self._add_coupon_row(coupon, prepend=True)

    def _add_coupon_row(self, coupon: Coupon, prepend: bool = False) -> None:
        """Create a coupon row widget."""
        row = ctk.CTkFrame(self.history_list, fg_color="gray18", corner_radius=8, height=34)
        row.pack_propagate(False)

        if prepend and self._coupon_rows:
            row.pack(fill="x", pady=1, padx=2, before=self._coupon_rows[0])
            self._coupon_rows.insert(0, row)
        else:
            row.pack(fill="x", pady=1, padx=2)
            self._coupon_rows.append(row)

        # Time
        time_str = coupon.detected_at.split(" ")[1][:8] if " " in coupon.detected_at else coupon.detected_at[:8]
        ctk.CTkLabel(
            row, text=time_str,
            font=ctk.CTkFont(size=10), text_color="gray50", width=70,
        ).pack(side="left", padx=5)

        # Account
        ctk.CTkLabel(
            row, text=f"@{coupon.account}" if coupon.account else "—",
            font=ctk.CTkFont(size=10), text_color="gray60", width=80,
            anchor="w",
        ).pack(side="left", padx=2)

        # Code (clickable to copy)
        code_btn = ctk.CTkButton(
            row,
            text=coupon.code,
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            fg_color="transparent",
            hover_color="gray25",
            text_color="#06b6d4",
            anchor="w",
            width=120,
            height=28,
            command=lambda c=coupon.code, b=None: self._copy_code(c, code_btn),
        )
        # Re-bind the button reference
        code_btn.configure(command=lambda c=coupon.code: self._copy_code(c, code_btn))
        code_btn.pack(side="left", padx=2)

        # Status dot
        status_color = "#10b981" if coupon.status == "detected" else "gray50"
        ctk.CTkLabel(
            row, text="●",
            font=ctk.CTkFont(size=10), text_color=status_color, width=50,
        ).pack(side="left", padx=5)

        # Store data for search
        row._coupon_data = coupon

    def _copy_code(self, code: str, button: ctk.CTkButton) -> None:
        """Copy code to clipboard and show feedback."""
        try:
            import pyperclip
            pyperclip.copy(code)
            original_text = button.cget("text")
            button.configure(text="✓ Copied", text_color="#10b981")
            self.after(1500, lambda: button.configure(text=original_text, text_color="#06b6d4"))
        except Exception:
            pass

    def _on_search(self) -> None:
        """Filter displayed coupons by search query."""
        query = self.search_input.get().strip().upper()
        for row in self._coupon_rows:
            coupon = row._coupon_data
            matches = (
                query in coupon.code.upper()
                or query in coupon.account.upper()
                or not query
            )
            if matches:
                row.pack(fill="x", pady=1, padx=2)
            else:
                row.pack_forget()
