"""
X (Twitter) monitor using Playwright with persistent browser profile.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Optional

# pyrefly: ignore [missing-import]
from playwright.async_api import async_playwright, BrowserContext, Page

from monitor.base import BaseMonitor, DetectedCoupon
from utils.coupon_detector import CouponDetector
from database.db import Database

logger = logging.getLogger("coupon_sniper.x_monitor")


class XMonitor(BaseMonitor):
    """
    Monitors X (Twitter) profile pages for new tweets containing coupon codes.
    Uses Playwright persistent Chromium context so the user only logs in once.
    """

    def __init__(
        self,
        db: Database,
        detector: CouponDetector,
        ocr_engine=None,
        profile_path: str = "./playwright_sessions",
        polling_interval_ms: int = 3000,
        headless: bool = False,
        enable_ocr: bool = False,
    ):
        super().__init__(platform="x")
        self.db = db
        self.detector = detector
        self.ocr_engine = ocr_engine
        self.profile_path = os.path.abspath(profile_path)
        self.polling_interval_s = polling_interval_ms / 1000.0
        self.headless = headless
        self.enable_ocr = enable_ocr

        self._context: Optional[BrowserContext] = None
        self._playwright = None
        self._tasks: dict[str, asyncio.Task] = {}
        self._pages: dict[str, Page] = {}
        self._running = False
        self._initialized_accounts: set[str] = set()

    async def _ensure_browser(self) -> BrowserContext:
        """Launch or return the persistent browser context."""
        if self._context is None:
            os.makedirs(self.profile_path, exist_ok=True)
            self._playwright = await async_playwright().start()
            self._context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=self.profile_path,
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"],
                viewport={"width": 1280, "height": 900},
            )
            self.emit_log("INFO", "Browser launched. Log in to X if needed.")
        return self._context

    async def _close_browser(self) -> None:
        """Close browser context."""
        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
            self._context = None
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

    async def _monitor_account(self, username: str) -> None:
        """Worker coroutine for a single account."""
        url = f"https://x.com/{username}"
        self.emit_log("INFO", f"Worker started for @{username}")
        self.emit_status(username, "starting", "Opening page...")

        try:
            context = await self._ensure_browser()
            page = await context.new_page()
            self._pages[username] = page

            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            self.emit_status(username, "monitoring", "Active")

            # Initial scan: record existing tweet IDs without processing
            first_scan = True

            while self._running and username in self._tasks:
                try:
                    # Wait for tweets to load
                    try:
                        await page.wait_for_selector(
                            'article[data-testid="tweet"]', timeout=15000
                        )
                    except Exception:
                        self.emit_status(username, "waiting", "No tweets loaded")
                        await asyncio.sleep(self.polling_interval_s)
                        try:
                            await page.reload(wait_until="domcontentloaded")
                        except Exception:
                            pass
                        continue

                    await asyncio.sleep(0.5)  # let content settle

                    tweet_elements = await page.query_selector_all(
                        'article[data-testid="tweet"]'
                    )

                    last_seen = self.db.get_last_seen_tweet_id(username)

                    for tweet_el in tweet_elements[:10]:
                        # Extract tweet ID from status link
                        link_el = await tweet_el.query_selector('a[href*="/status/"]')
                        if not link_el:
                            continue
                        href = await link_el.get_attribute("href")
                        if not href or "/status/" not in href:
                            continue
                        tweet_id = href.split("/status/")[1].split("?")[0].split("/")[0]

                        if tweet_id == last_seen:
                            break  # We've caught up

                        if first_scan:
                            # On first scan, just record the newest tweet ID
                            self.db.set_last_seen_tweet_id(username, tweet_id)
                            self.emit_log(
                                "INFO",
                                f"@{username}: Initial scan, recorded tweet {tweet_id}",
                            )
                            break  # only need the first (newest) one

                        # ── Process new tweet ──────────────────────────
                        tweet_url = f"https://x.com{href}"

                        # Extract text
                        text_el = await tweet_el.query_selector(
                            'div[data-testid="tweetText"]'
                        )
                        tweet_text = (
                            await text_el.inner_text() if text_el else ""
                        )

                        self.emit_log("INFO", f"@{username}: New tweet {tweet_id}")

                        # Detect coupons from text
                        codes = self.detector.detect(tweet_text)

                        # If no codes and OCR is enabled, try images
                        if not codes and self.enable_ocr and self.ocr_engine:
                            codes = await self._try_ocr_on_images(
                                tweet_el, username, tweet_id, tweet_text
                            )

                        # Update last seen
                        self.db.set_last_seen_tweet_id(username, tweet_id)

                        if codes:
                            for code in codes:
                                if not self.db.is_duplicate_coupon(code):
                                    self.db.save_coupon(
                                        code=code,
                                        tweet_url=tweet_url,
                                        tweet_id=tweet_id,
                                        account=username,
                                    )
                                    self.emit_coupon(
                                        DetectedCoupon(
                                            code=code,
                                            account=username,
                                            platform="x",
                                            tweet_url=tweet_url,
                                            tweet_id=tweet_id,
                                            tweet_text=tweet_text,
                                        )
                                    )
                                    self.emit_log(
                                        "COUPON",
                                        f"🎯 COUPON FOUND from @{username}: {code}",
                                    )
                                else:
                                    self.emit_log(
                                        "INFO",
                                        f"Duplicate coupon ignored: {code}",
                                    )
                        else:
                            self.emit_log(
                                "DEBUG",
                                f"@{username}: No coupon in tweet {tweet_id[:8]}...",
                            )

                    if first_scan:
                        first_scan = False
                        self.emit_log(
                            "INFO",
                            f"@{username}: Initial scan complete, now monitoring",
                        )

                    self.emit_status(
                        username,
                        "monitoring",
                        f"Last poll: {time.strftime('%H:%M:%S')}",
                    )

                    # Soft refresh strategy
                    iteration = getattr(self, f"_iter_{username}", 0)
                    setattr(self, f"_iter_{username}", iteration + 1)

                    if iteration % 5 == 0:
                        # Full reload every 5th iteration
                        try:
                            await page.reload(wait_until="domcontentloaded")
                        except Exception:
                            await page.goto(url, wait_until="domcontentloaded")
                    else:
                        # Scroll to top to trigger lazy loading
                        await page.evaluate("window.scrollTo(0, 0)")

                    await asyncio.sleep(self.polling_interval_s)

                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    err_msg = str(e)
                    if "Execution context was destroyed" not in err_msg:
                        self.emit_log("ERROR", f"@{username} error: {err_msg}")
                        self.emit_status(username, "error", "Reconnecting...")
                    await asyncio.sleep(5)
                    try:
                        await page.goto(url, wait_until="domcontentloaded")
                    except Exception:
                        pass

        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.emit_log("ERROR", f"@{username} worker crashed: {e}")
            self.emit_status(username, "crashed", str(e))
        finally:
            # Cleanup page
            if username in self._pages:
                try:
                    await self._pages[username].close()
                except Exception:
                    pass
                del self._pages[username]
            self.emit_log("INFO", f"Worker stopped for @{username}")
            self.emit_status(username, "stopped", "")

    async def _try_ocr_on_images(
        self, tweet_el, username: str, tweet_id: str, tweet_text: str
    ) -> list[str]:
        """Capture DOM screenshots of tweet images in RAM and run parallel OCR with instant early exit."""
        codes: list[str] = []
        try:
            img_elements = await tweet_el.query_selector_all(
                'div[data-testid="tweetPhoto"] img'
            )
            if not img_elements:
                return []

            loop = asyncio.get_running_loop()

            async def _process_single_img(img_el):
                try:
                    # Capture screenshot directly from DOM cache into RAM bytes (<15ms)
                    img_bytes = await img_el.screenshot(type="png")
                    ocr_text = await loop.run_in_executor(
                        None, self.ocr_engine.extract_text, img_bytes
                    )
                    if ocr_text:
                        return self.detector.detect_from_ocr(ocr_text)
                except Exception as e:
                    logger.warning(f"Single image OCR error: {e}")
                return []

            # Run image captures and OCR in parallel for up to 3 images
            tasks = [asyncio.create_task(_process_single_img(img_el)) for img_el in img_elements[:3]]
            
            for completed_task in asyncio.as_completed(tasks):
                res_codes = await completed_task
                if res_codes:
                    codes.extend(res_codes)
                    self.emit_log("INFO", f"⚡ Ultra-Fast OCR found code: {res_codes}")
                    # Early exit: cancel remaining image OCR tasks immediately
                    for t in tasks:
                        if not t.done():
                            t.cancel()
                    break

        except Exception as e:
            self.emit_log("ERROR", f"OCR scan error: {e}")
        return codes


    # ── Public API ────────────────────────────────────────────────

    async def start_monitoring(self, usernames: list[str]) -> None:
        """Start monitoring the given accounts."""
        self._running = True
        await self._ensure_browser()
        for username in usernames:
            username = username.lstrip("@").strip().lower()
            if username not in self._tasks or self._tasks[username].done():
                task = asyncio.create_task(self._monitor_account(username))
                self._tasks[username] = task

    async def stop_monitoring(self) -> None:
        """Stop all monitoring workers and close browser."""
        self._running = False
        for username, task in list(self._tasks.items()):
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        self._tasks.clear()
        await self._close_browser()
        self.emit_log("INFO", "All workers stopped.")

    async def add_account(self, username: str) -> None:
        """Add and start monitoring a new account."""
        username = username.lstrip("@").strip().lower()
        if self._running and (username not in self._tasks or self._tasks[username].done()):
            task = asyncio.create_task(self._monitor_account(username))
            self._tasks[username] = task

    async def remove_account(self, username: str) -> None:
        """Stop and remove an account from monitoring."""
        username = username.lstrip("@").strip().lower()
        if username in self._tasks:
            self._tasks[username].cancel()
            try:
                await self._tasks[username]
            except (asyncio.CancelledError, Exception):
                pass
            del self._tasks[username]

    def get_active_workers(self) -> list[str]:
        """Return list of currently active worker usernames."""
        return [u for u, t in self._tasks.items() if not t.done()]

    def update_polling_interval(self, ms: int) -> None:
        self.polling_interval_s = ms / 1000.0
