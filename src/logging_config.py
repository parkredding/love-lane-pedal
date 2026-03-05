"""
Logging configuration for StemStomp.

Sets up structured logging via Python's logging module.
All output goes to stderr (captured by systemd journald).
"""

from __future__ import annotations

import logging


def setup_logging(level: str = "INFO") -> None:
    """Configure the root stemstomp logger."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(name)s] %(levelname)s %(message)s")
    )
    root = logging.getLogger("stemstomp")
    root.setLevel(numeric_level)
    if not root.handlers:
        root.addHandler(handler)
