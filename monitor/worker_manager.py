"""
Manages the async event loop in a background thread,
bridging the synchronous CustomTkinter GUI with async Playwright workers.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from typing import Optional, Callable

from monitor.x_monitor import XMonitor
from monitor.base import DetectedCoupon
from database.db import Database
from utils.coupon_detector import CouponDetector
from config.settings import AppSettings

logger = logging.getLogger("coupon_sniper.worker_manager")


class WorkerManager:
    """
    Runs the async monitoring loop in a background thread.
    Provides a sync API for the GUI to start/stop monitoring and add/remove accounts.
    """

    def __init__(
        self,
        db: Database,
        settings: AppSettings,
        on_coupon: Optional[Callable[[DetectedCoupon], None]] = None,
        on_log: Optional[Callable[[str, str], None]] = None,
        on_status: Optional[Callable[[str, str, str], None]] = None,
    ):
        self.db = db
        self.settings = settings
        self._on_coupon = on_coupon
        self._on_log = on_log
        self._on_status = on_status

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._monitor: Optional[XMonitor] = None
        self._running = False

    def _create_monitor(self) -> XMonitor:
        """Create a new XMonitor instance with current settings."""
        detector = CouponDetector(pattern=self.settings.coupon_regex)

        ocr_engine = None
        if self.settings.enable_ocr:
            try:
                from ocr.ocr_engine import OCREngine
                ocr_engine = OCREngine()
                ocr_engine.warmup()
            except Exception as e:
                logger.error(f"Failed to initialize OCR: {e}")


        monitor = XMonitor(
            db=self.db,
            detector=detector,
            ocr_engine=ocr_engine,
            profile_path=self.settings.browser_profile_path,
            polling_interval_ms=self.settings.polling_interval_ms,
            headless=self.settings.headless,
            enable_ocr=self.settings.enable_ocr,
        )
        monitor.set_callbacks(
            on_coupon=self._on_coupon,
            on_log=self._on_log,
            on_status=self._on_status,
        )
        return monitor

    def _run_loop(self, usernames: list[str]) -> None:
        """Target for the background thread — runs the asyncio event loop."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._monitor = self._create_monitor()
            self._loop.run_until_complete(self._monitor.start_monitoring(usernames))
            # Keep loop running until stop is called
            self._loop.run_forever()
        except Exception as e:
            logger.error(f"Worker loop crashed: {e}")
        finally:
            # Cleanup
            if self._monitor:
                try:
                    self._loop.run_until_complete(self._monitor.stop_monitoring())
                except Exception:
                    pass
            self._loop.close()
            self._loop = None
            self._running = False

    def start(self, usernames: list[str]) -> None:
        """Start monitoring in a background thread. Non-blocking."""
        if self._running:
            logger.warning("Workers already running")
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop,
            args=(usernames,),
            daemon=True,
            name="MonitorThread",
        )
        self._thread.start()
        logger.info(f"Started monitoring {len(usernames)} accounts")

    def stop(self, on_complete: Optional[Callable[[], None]] = None) -> None:
        """Stop all workers and the background loop. Non-blocking."""
        if not self._running:
            if on_complete:
                on_complete()
            return

        self._running = False

        def _do_stop():
            """Run the actual stop in a separate thread so Tkinter doesn't freeze."""
            if self._loop and self._monitor:
                future = asyncio.run_coroutine_threadsafe(
                    self._monitor.stop_monitoring(), self._loop
                )
                try:
                    future.result(timeout=15)
                except Exception as e:
                    logger.warning(f"Stop monitor timed out or errored: {e}")

            if self._loop:
                self._loop.call_soon_threadsafe(self._loop.stop)

            if self._thread:
                self._thread.join(timeout=10)
                self._thread = None

            logger.info("All workers stopped")
            if on_complete:
                on_complete()

        threading.Thread(target=_do_stop, daemon=True, name="StopThread").start()

    def add_account(self, username: str) -> None:
        """Add an account to live monitoring."""
        if self._loop and self._monitor and self._running:
            asyncio.run_coroutine_threadsafe(
                self._monitor.add_account(username), self._loop
            )

    def remove_account(self, username: str) -> None:
        """Remove an account from live monitoring."""
        if self._loop and self._monitor and self._running:
            asyncio.run_coroutine_threadsafe(
                self._monitor.remove_account(username), self._loop
            )

    def get_active_workers(self) -> list[str]:
        """Return list of active worker usernames."""
        if self._monitor:
            return self._monitor.get_active_workers()
        return []

    def update_settings(self, settings: AppSettings) -> None:
        """Update settings (applied on next start)."""
        self.settings = settings
        if self._monitor:
            self._monitor.update_polling_interval(settings.polling_interval_ms)

    @property
    def is_running(self) -> bool:
        return self._running
