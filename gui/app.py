"""
Main application window — brings all panels together.
"""
from __future__ import annotations

# pyrefly: ignore [missing-import]
import customtkinter as ctk
import logging
import os
import threading
import webbrowser
from datetime import datetime
from tkinter import filedialog, messagebox
from typing import Optional

from config.settings import AppSettings
from database.db import Database, Coupon
from gui.sidebar import Sidebar
from gui.center_panel import CenterPanel
from gui.log_panel import LogPanel
from gui.history_panel import HistoryPanel
from gui.settings_dialog import SettingsDialog
from monitor.base import DetectedCoupon
from monitor.worker_manager import WorkerManager
from notifications.notifier import Notifier

logger = logging.getLogger("coupon_sniper.gui")


class CouponSniperApp(ctk.CTk):
    """Main application window for Coupon Sniper."""

    def __init__(self):
        super().__init__()

        # ── Initialize core systems ──
        self.settings = AppSettings.load()
        self.db = Database()
        self.notifier = Notifier(
            enable_clipboard=self.settings.enable_clipboard,
            enable_sound=self.settings.enable_sound,
            enable_notification=self.settings.enable_notification,
        )

        # Worker manager with thread-safe callbacks
        self.worker_manager = WorkerManager(
            db=self.db,
            settings=self.settings,
            on_coupon=self._on_coupon_found,
            on_log=self._on_log,
            on_status=self._on_status_update,
        )

        # ── Configure window ──
        self.title("Coupon Sniper")
        self.geometry("1400x850")
        self.minsize(1100, 700)

        ctk.set_appearance_mode(self.settings.theme)
        ctk.set_default_color_theme("blue")

        # ── Build layout ──
        self._build_layout()

        # ── Load initial data ──
        self._load_accounts()
        self._load_history()
        self._update_stats()

        # ── Periodic stats updater ──
        self._start_stats_updater()

        # ── Auto-start if configured ──
        if self.settings.auto_start_monitoring:
            self.after(1000, self._start_monitoring)

        # ── Handle close ──
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._log("INFO", "Coupon Sniper ready")

    def _build_layout(self) -> None:
        """Build the three-panel layout with bottom log panel."""
        # Main container
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)

        # Left sidebar
        self.sidebar = Sidebar(
            main_frame,
            on_start=self._start_monitoring,
            on_stop=self._stop_monitoring,
            on_add_account=self._add_account,
            on_remove_account=self._remove_account,
            on_toggle_account=self._toggle_account,
            on_open_settings=self._open_settings,
            width=280,
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        # Center panel
        self.center_panel = CenterPanel(main_frame)
        self.center_panel.grid(row=0, column=1, sticky="nsew", padx=5)

        # Right history panel
        self.history_panel = HistoryPanel(
            main_frame,
            on_export_csv=self._export_csv,
            width=350,
        )
        self.history_panel.grid(row=0, column=2, sticky="nsew", padx=(5, 0))

        # Bottom log panel (spans full width)
        self.log_panel = LogPanel(self, height=180)
        self.log_panel.pack(fill="x", padx=10, pady=(0, 10))

    # ── Account Management ────────────────────────────────────────

    def _load_accounts(self) -> None:
        """Load accounts from database and populate sidebar."""
        accounts = self.db.get_accounts()
        if not accounts:
            # Seed with default accounts on first run
            for username in self.settings.default_accounts:
                self.db.add_account(username)
            accounts = self.db.get_accounts()

        for acct in accounts:
            self.sidebar.add_account_widget(acct.username, acct.enabled)

    def _add_account(self, username: str) -> None:
        """Add a new account to monitor."""
        username = username.lstrip("@").strip().lower()
        if not username:
            return

        if self.db.add_account(username):
            self.sidebar.add_account_widget(username, True)
            self._log("INFO", f"Account added: @{username}")

            # If monitoring is active, start worker for new account
            if self.worker_manager.is_running:
                self.worker_manager.add_account(username)
        else:
            self._log("WARNING", f"Account @{username} already exists")

    def _remove_account(self, username: str) -> None:
        """Remove an account from monitoring."""
        username = username.lstrip("@").strip().lower()
        self.db.remove_account(username)
        self.sidebar.remove_account_widget(username)
        self._log("INFO", f"Account removed: @{username}")

        if self.worker_manager.is_running:
            self.worker_manager.remove_account(username)

    def _toggle_account(self, username: str, enabled: bool) -> None:
        """Enable/disable an account."""
        self.db.toggle_account(username, enabled)
        state = "enabled" if enabled else "disabled"
        self._log("INFO", f"Account @{username} {state}")

    # ── Monitoring Control ────────────────────────────────────────

    def _start_monitoring(self) -> None:
        """Start all enabled account workers."""
        accounts = self.db.get_accounts(enabled_only=True)
        if not accounts:
            self._log("WARNING", "No enabled accounts to monitor")
            self.sidebar.set_monitoring_state(False)
            return

        usernames = [a.username for a in accounts]
        self._log("INFO", f"Starting monitoring for {len(usernames)} accounts...")
        self.sidebar.set_monitoring_state(True)
        self.center_panel.set_monitoring_status(True)

        self.worker_manager.start(usernames)

    def _stop_monitoring(self) -> None:
        """Stop all workers."""
        self._log("INFO", "Stopping all workers...")
        self.worker_manager.stop()
        self.sidebar.set_monitoring_state(False)
        self.center_panel.set_monitoring_status(False)
        self._log("INFO", "All workers stopped")

    # ── Callbacks (called from worker thread — must use after()) ──

    def _on_coupon_found(self, coupon: DetectedCoupon) -> None:
        """Called from worker thread when a coupon is detected."""
        def _update():
            # Alert user
            self.notifier.alert_coupon_found(coupon.code, coupon.account)

            # Update UI
            self.center_panel.set_latest_coupon(coupon.code, coupon.account)

            # Add to history panel
            db_coupon = Coupon(
                id=None,
                code=coupon.code,
                tweet_url=coupon.tweet_url,
                tweet_id=coupon.tweet_id,
                account=coupon.account,
                detected_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                status="detected",
            )
            self.history_panel.add_coupon(db_coupon)

            # Open redemption page if configured
            if self.settings.open_redemption_page and self.settings.redemption_url:
                try:
                    webbrowser.open(self.settings.redemption_url)
                except Exception:
                    pass

            self._update_stats()

            # Log to database
            self.db.save_log("COUPON", f"Found: {coupon.code} from @{coupon.account}")

        self.after(0, _update)

    def _on_log(self, level: str, message: str) -> None:
        """Called from worker thread for log messages."""
        self.after(0, lambda: self._log(level, message))

    def _on_status_update(self, username: str, status: str, detail: str) -> None:
        """Called from worker thread for account status changes."""
        def _update():
            self.sidebar.update_account_status(username, status, detail)
            if status == "monitoring":
                self.center_panel.update_last_poll()
        self.after(0, _update)

    # ── Logging ───────────────────────────────────────────────────

    def _log(self, level: str, message: str) -> None:
        """Add a log entry to both UI and database."""
        self.log_panel.add_log(level, message)
        # Save to DB in background
        threading.Thread(
            target=self.db.save_log, args=(level, message), daemon=True
        ).start()

    # ── History & Stats ───────────────────────────────────────────

    def _load_history(self) -> None:
        """Load coupon history from database."""
        coupons = self.db.get_coupon_history(limit=100)
        self.history_panel.load_history(coupons)

    def _update_stats(self) -> None:
        """Update statistics display."""
        accounts = self.db.get_accounts(enabled_only=True)
        workers = self.worker_manager.get_active_workers()
        today = self.db.get_coupons_today_count()
        total = len(self.db.get_coupon_history(limit=100000))

        self.center_panel.update_stats(
            monitoring=len(accounts),
            workers=len(workers),
            today=today,
            total=total,
        )

    def _start_stats_updater(self) -> None:
        """Periodically update stats display."""
        def _tick():
            if self.worker_manager.is_running:
                self._update_stats()
            self.after(5000, _tick)
        self.after(5000, _tick)

    def _export_csv(self) -> None:
        """Export coupon history to CSV file."""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Export Coupon History",
            initialfile=f"coupons_{datetime.now().strftime('%Y%m%d')}.csv",
        )
        if filepath:
            try:
                csv_data = self.db.export_csv()
                with open(filepath, "w", encoding="utf-8", newline="") as f:
                    f.write(csv_data)
                self._log("INFO", f"Exported {filepath}")
                messagebox.showinfo("Export Complete", f"Saved to {filepath}")
            except Exception as e:
                self._log("ERROR", f"Export failed: {e}")
                messagebox.showerror("Export Failed", str(e))

    # ── Settings ──────────────────────────────────────────────────

    def _open_settings(self) -> None:
        """Open the settings dialog."""
        SettingsDialog(
            self,
            settings=self.settings,
            on_save=self._apply_settings,
        )

    def _apply_settings(self, settings: AppSettings) -> None:
        """Apply updated settings."""
        self.settings = settings
        self.worker_manager.update_settings(settings)
        self.notifier.update_settings(
            enable_clipboard=settings.enable_clipboard,
            enable_sound=settings.enable_sound,
            enable_notification=settings.enable_notification,
        )
        ctk.set_appearance_mode(settings.theme)
        self._log("INFO", "Settings saved and applied")

    # ── Cleanup ───────────────────────────────────────────────────

    def _on_close(self) -> None:
        """Clean shutdown."""
        self._log("INFO", "Shutting down...")
        self.sidebar.set_monitoring_state(False)
        self.center_panel.set_monitoring_status(False)

        # Hide window immediately so the user knows shutdown has started
        self.withdraw()

        def _finish_close():
            self.destroy()

        if self.worker_manager.is_running:
            self.worker_manager.stop(on_complete=lambda: self.after(0, _finish_close))
        else:
            self.destroy()
