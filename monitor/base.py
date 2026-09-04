"""
Abstract base class for platform monitors.
Enables plugin architecture for future platforms (Discord, Telegram, etc.).
"""
from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class DetectedCoupon:
    """Data object for a detected coupon event."""
    code: str
    account: str
    platform: str
    tweet_url: str = ""
    tweet_id: str = ""
    tweet_text: str = ""


# Type alias for the callback
CouponCallback = Callable[[DetectedCoupon], None]
LogCallback = Callable[[str, str], None]  # (level, message)
StatusCallback = Callable[[str, str, str], None]  # (username, status, detail)


class BaseMonitor(abc.ABC):
    """
    Abstract base for all platform monitors.
    Subclasses implement the actual scraping/polling logic.
    """

    def __init__(self, platform: str):
        self.platform = platform
        self._on_coupon: Optional[CouponCallback] = None
        self._on_log: Optional[LogCallback] = None
        self._on_status: Optional[StatusCallback] = None

    def set_callbacks(
        self,
        on_coupon: Optional[CouponCallback] = None,
        on_log: Optional[LogCallback] = None,
        on_status: Optional[StatusCallback] = None,
    ) -> None:
        """Register callback functions for events."""
        if on_coupon:
            self._on_coupon = on_coupon
        if on_log:
            self._on_log = on_log
        if on_status:
            self._on_status = on_status

    def emit_coupon(self, coupon: DetectedCoupon) -> None:
        if self._on_coupon:
            self._on_coupon(coupon)

    def emit_log(self, level: str, message: str) -> None:
        if self._on_log:
            self._on_log(level, message)

    def emit_status(self, username: str, status: str, detail: str = "") -> None:
        if self._on_status:
            self._on_status(username, status, detail)

    @abc.abstractmethod
    async def start_monitoring(self, usernames: list[str]) -> None:
        """Start monitoring the given accounts."""
        ...

    @abc.abstractmethod
    async def stop_monitoring(self) -> None:
        """Stop all monitoring workers."""
        ...

    @abc.abstractmethod
    async def add_account(self, username: str) -> None:
        """Add an account to active monitoring."""
        ...

    @abc.abstractmethod
    async def remove_account(self, username: str) -> None:
        """Remove an account from active monitoring."""
        ...
