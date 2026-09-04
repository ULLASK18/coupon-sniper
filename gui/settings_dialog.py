"""
Settings dialog window.
"""
from __future__ import annotations

import customtkinter as ctk
from config.settings import AppSettings
from typing import Callable, Optional


class SettingsDialog(ctk.CTkToplevel):
    """Modal settings window for all configurable options."""

    def __init__(
        self,
        master,
        settings: AppSettings,
        on_save: Optional[Callable[[AppSettings], None]] = None,
    ):
        super().__init__(master)
        self.settings = settings
        self._on_save = on_save

        self.title("Settings — Coupon Sniper")
        self.geometry("500x620")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() // 2) - 250
        y = master.winfo_y() + (master.winfo_height() // 2) - 310
        self.geometry(f"+{x}+{y}")

        self._vars: dict = {}
        self._build()

    def _build(self) -> None:
        # Scrollable content
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=15, pady=10)

        # ── Monitoring Section ──
        self._section(scroll, "MONITORING")

        self._add_entry(scroll, "Polling Interval (ms)", "polling_interval_ms",
                        str(self.settings.polling_interval_ms))
        self._add_entry(scroll, "Max Workers", "max_workers",
                        str(self.settings.max_workers))
        self._add_switch(scroll, "Auto-Start Monitoring", "auto_start_monitoring",
                         self.settings.auto_start_monitoring)

        # ── Detection Section ──
        self._section(scroll, "DETECTION")

        self._add_entry(scroll, "Coupon Regex", "coupon_regex",
                        self.settings.coupon_regex)
        self._add_switch(scroll, "Enable OCR (EasyOCR)", "enable_ocr",
                         self.settings.enable_ocr)

        # ── Notifications Section ──
        self._section(scroll, "NOTIFICATIONS")

        self._add_switch(scroll, "Sound Alert", "enable_sound",
                         self.settings.enable_sound)
        self._add_switch(scroll, "Windows Notification", "enable_notification",
                         self.settings.enable_notification)
        self._add_switch(scroll, "Auto-Copy to Clipboard", "enable_clipboard",
                         self.settings.enable_clipboard)

        # ── Browser Section ──
        self._section(scroll, "BROWSER")

        self._add_entry(scroll, "Profile Path", "browser_profile_path",
                        self.settings.browser_profile_path)
        self._add_switch(scroll, "Headless Mode", "headless",
                         self.settings.headless)

        # ── Redemption Section ──
        self._section(scroll, "REDEMPTION")

        self._add_entry(scroll, "Redemption URL", "redemption_url",
                        self.settings.redemption_url)
        self._add_switch(scroll, "Auto-Open Redemption Page", "open_redemption_page",
                         self.settings.open_redemption_page)

        # ── UI Section ──
        self._section(scroll, "APPEARANCE")

        theme_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        theme_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(theme_frame, text="Theme", font=ctk.CTkFont(size=12)).pack(side="left")
        self._vars["theme"] = ctk.StringVar(value=self.settings.theme)
        ctk.CTkSegmentedButton(
            theme_frame,
            values=["dark", "light", "system"],
            variable=self._vars["theme"],
            font=ctk.CTkFont(size=11),
        ).pack(side="right")

        # ── Buttons ──
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=15)

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            fg_color="gray25",
            hover_color="gray35",
            width=100,
            command=self.destroy,
        ).pack(side="left")

        ctk.CTkButton(
            btn_frame,
            text="Save Settings",
            fg_color="#10b981",
            hover_color="#059669",
            width=140,
            font=ctk.CTkFont(weight="bold"),
            command=self._save,
        ).pack(side="right")

    def _section(self, parent, title: str) -> None:
        ctk.CTkLabel(
            parent,
            text=title,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="gray50",
        ).pack(anchor="w", pady=(15, 5))

        # Separator line
        sep = ctk.CTkFrame(parent, height=1, fg_color="gray25")
        sep.pack(fill="x", pady=(0, 5))

    def _add_entry(self, parent, label: str, key: str, default: str) -> None:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=3)

        ctk.CTkLabel(
            frame, text=label, font=ctk.CTkFont(size=12),
        ).pack(side="left")

        var = ctk.StringVar(value=default)
        self._vars[key] = var
        ctk.CTkEntry(
            frame, textvariable=var, width=200,
            font=ctk.CTkFont(size=11),
        ).pack(side="right")

    def _add_switch(self, parent, label: str, key: str, default: bool) -> None:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=3)

        ctk.CTkLabel(
            frame, text=label, font=ctk.CTkFont(size=12),
        ).pack(side="left")

        var = ctk.BooleanVar(value=default)
        self._vars[key] = var
        ctk.CTkSwitch(
            frame, text="", variable=var,
            onvalue=True, offvalue=False,
            switch_width=36, switch_height=18,
        ).pack(side="right")

    def _save(self) -> None:
        """Collect values and save settings."""
        try:
            self.settings.polling_interval_ms = int(self._vars["polling_interval_ms"].get())
        except ValueError:
            pass
        try:
            self.settings.max_workers = int(self._vars["max_workers"].get())
        except ValueError:
            pass

        self.settings.auto_start_monitoring = self._vars["auto_start_monitoring"].get()
        self.settings.coupon_regex = self._vars["coupon_regex"].get()
        self.settings.enable_ocr = self._vars["enable_ocr"].get()
        self.settings.enable_sound = self._vars["enable_sound"].get()
        self.settings.enable_notification = self._vars["enable_notification"].get()
        self.settings.enable_clipboard = self._vars["enable_clipboard"].get()
        self.settings.browser_profile_path = self._vars["browser_profile_path"].get()
        self.settings.headless = self._vars["headless"].get()
        self.settings.redemption_url = self._vars["redemption_url"].get()
        self.settings.open_redemption_page = self._vars["open_redemption_page"].get()
        self.settings.theme = self._vars["theme"].get()

        self.settings.save()

        if self._on_save:
            self._on_save(self.settings)

        self.destroy()
