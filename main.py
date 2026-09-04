"""
Coupon Sniper — Entry Point

A desktop application to monitor X (Twitter) accounts for coupon codes.
Detects codes, copies them to clipboard, and alerts instantly.
"""
import logging
import os
import sys

# Ensure project root is on the path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def setup_logging() -> None:
    """Configure application logging."""
    log_dir = os.path.join(PROJECT_ROOT, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "coupon_sniper.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def main() -> None:
    setup_logging()
    logger = logging.getLogger("coupon_sniper")
    logger.info("Starting Coupon Sniper...")

    from gui.app import CouponSniperApp

    app = CouponSniperApp()
    app.mainloop()


if __name__ == "__main__":
    main()
