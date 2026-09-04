"""
Application settings with JSON persistence.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional


CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(CONFIG_DIR), "config.json")


@dataclass
class AppSettings:
    """All user-configurable settings for Coupon Sniper."""

    # Monitoring
    polling_interval_ms: int = 3000
    max_workers: int = 20
    auto_start_monitoring: bool = False

    # Detection
    coupon_regex: str = r"\b[A-Z0-9]{3,}-[A-Z0-9]{3,}\b"
    enable_ocr: bool = True

    # Notifications
    enable_sound: bool = True
    enable_clipboard: bool = True
    enable_notification: bool = True

    # Browser
    browser_profile_path: str = "./x_monitor_session"
    headless: bool = False

    # Redemption
    redemption_url: str = ""
    open_redemption_page: bool = False

    # UI
    theme: str = "dark"  # "dark", "light", "system"

    # Default monitored accounts
    default_accounts: list[str] = field(default_factory=lambda: [
        "khushman",
        "lucidtrading",
        "fundingpips",
    ])

    def save(self, path: Optional[str] = None) -> None:
        """Persist settings to JSON file."""
        path = path or DEFAULT_CONFIG_PATH
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls, path: Optional[str] = None) -> "AppSettings":
        """Load settings from JSON file, falling back to defaults."""
        path = path or DEFAULT_CONFIG_PATH
        if not os.path.exists(path):
            settings = cls()
            settings.save(path)
            return settings
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Only use known fields (ignore stale keys from old configs)
            known_fields = {fld.name for fld in cls.__dataclass_fields__.values()}
            filtered = {k: v for k, v in data.items() if k in known_fields}
            return cls(**filtered)
        except (json.JSONDecodeError, TypeError, KeyError):
            return cls()
