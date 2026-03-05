"""
Health check module for StemStomp.

Provides system status information for monitoring and diagnostics.
"""

from __future__ import annotations

import json
import logging
import shutil
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("stemstomp.health")


class HealthCheck:
    """Collects and reports system health metrics."""

    def __init__(
        self,
        stems_dir: Path,
        version_file: Path | None = None,
    ) -> None:
        self._stems_dir = stems_dir
        self._version_file = version_file or (
            Path(__file__).resolve().parent.parent / "version.txt"
        )
        self._start_time = time.monotonic()

    def collect(self) -> dict[str, Any]:
        """Return a dict of current health metrics."""
        return {
            "version": self._read_version(),
            "uptime_seconds": int(time.monotonic() - self._start_time),
            "stem_count": self._count_stems(),
            "disk_free_mb": self._disk_free_mb(),
        }

    def write_status(self, path: Path | None = None) -> None:
        """Write health status to a JSON file."""
        if path is None:
            path = Path("/tmp/stemstomp_health.json")
        try:
            status = self.collect()
            path.write_text(json.dumps(status, indent=2) + "\n")
        except Exception as exc:
            logger.debug("Failed to write health status: %s", exc)

    def _read_version(self) -> str:
        try:
            return self._version_file.read_text().strip()
        except FileNotFoundError:
            return "unknown"

    def _count_stems(self) -> int:
        if not self._stems_dir.exists():
            return 0
        return len(list(self._stems_dir.glob("*.wav")))

    def _disk_free_mb(self) -> int:
        try:
            usage = shutil.disk_usage(self._stems_dir)
            return int(usage.free / (1024 * 1024))
        except (OSError, FileNotFoundError):
            return -1
