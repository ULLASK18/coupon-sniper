"""
Notification system: clipboard, sound, Windows toast.
"""
from __future__ import annotations

import threading
import logging

logger = logging.getLogger("coupon_sniper.notifications")


class Notifier:
    """Handles all alert channels: clipboard, sound, Windows toast notification."""

    def __init__(
        self,
        enable_clipboard: bool = True,
        enable_sound: bool = True,
        enable_notification: bool = True,
    ):
        self.enable_clipboard = enable_clipboard
        self.enable_sound = enable_sound
        self.enable_notification = enable_notification

    def update_settings(
        self,
        enable_clipboard: bool | None = None,
        enable_sound: bool | None = None,
        enable_notification: bool | None = None,
    ) -> None:
        if enable_clipboard is not None:
            self.enable_clipboard = enable_clipboard
        if enable_sound is not None:
            self.enable_sound = enable_sound
        if enable_notification is not None:
            self.enable_notification = enable_notification

    def copy_to_clipboard(self, text: str) -> bool:
        """Copy text to clipboard using pyperclip."""
        if not self.enable_clipboard:
            return False
        try:
            import pyperclip
            pyperclip.copy(text)
            logger.info(f"Clipboard updated: {text}")
            return True
        except Exception as e:
            logger.error(f"Clipboard error: {e}")
            return False

    def play_sound(self) -> None:
        """Play a loud Windows notification sound (non-blocking)."""
        if not self.enable_sound:
            return

        def _play():
            try:
                import winsound
                # Play the system exclamation sound
                winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS | winsound.SND_ASYNC)
                # Also do a series of beeps for urgency
                for freq in [1200, 1500, 1800, 1500, 1200]:
                    winsound.Beep(freq, 120)
            except Exception as e:
                logger.error(f"Sound error: {e}")

        threading.Thread(target=_play, daemon=True).start()

    def show_toast(self, title: str, message: str) -> None:
        """Show a Windows toast notification (non-blocking)."""
        if not self.enable_notification:
            return

        def _notify():
            try:
                from plyer import notification
                notification.notify(
                    title=title,
                    message=message,
                    app_name="Coupon Sniper",
                    timeout=10,
                )
            except Exception as e:
                logger.error(f"Toast notification error: {e}")

        threading.Thread(target=_notify, daemon=True).start()

    def alert_coupon_found(self, code: str, account: str = "") -> None:
        """Full alert pipeline: clipboard + sound + toast."""
        source = f" from @{account}" if account else ""
        logger.info(f"COUPON FOUND{source}: {code}")

        self.copy_to_clipboard(code)
        self.play_sound()
        self.show_toast(
            title="🎯 Coupon Sniped!",
            message=f"Code: {code}{source}",
        )
