"""
Network / Wi-Fi management for StemStomp.

Relies on the system having NetworkManager (nmcli) available.
balena-wifi-connect is used for the captive portal AP mode.

All external commands are executed via subprocess so they can be
mocked easily in tests.
"""

from __future__ import annotations

import logging
import subprocess
import time
from enum import Enum, auto
from typing import Optional

logger = logging.getLogger("stemstomp.network")


class NetworkState(Enum):
    CONNECTED = auto()
    DISCONNECTED = auto()
    AP_MODE = auto()
    PROVISIONING = auto()


class NetworkManager:
    """
    Manages Wi-Fi connectivity and captive portal provisioning.

    On non-Pi hardware the class can be constructed with
    ``dry_run=True`` to skip actual subprocess calls; the caller is
    responsible for injecting state for testing.
    """

    AP_SSID = "StemStomp-Setup"
    CHECK_INTERVAL = 5  # seconds between connectivity polls

    def __init__(self, dry_run: bool = False) -> None:
        self._dry_run = dry_run
        self._state: NetworkState = NetworkState.DISCONNECTED

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def state(self) -> NetworkState:
        return self._state

    def resolve(self) -> NetworkState:
        """
        Attempt to find a known network. If none is found, start the
        captive portal and block until credentials are saved.

        Returns the final NetworkState.
        """
        if self._check_connected():
            self._state = NetworkState.CONNECTED
            return self._state

        # No known network – launch captive portal
        self._state = NetworkState.AP_MODE
        self._start_ap()

        # Poll until wifi-connect exits (credentials saved + connected)
        self._state = NetworkState.PROVISIONING
        self._wait_for_connection()

        if self._check_connected():
            self._state = NetworkState.CONNECTED
        else:
            self._state = NetworkState.DISCONNECTED

        return self._state

    def is_connected(self) -> bool:
        """Non-blocking connectivity check."""
        return self._check_connected()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_connected(self) -> bool:
        """Return True if a Wi-Fi connection is active."""
        if self._dry_run:
            return False
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "CONNECTIVITY", "general"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return "full" in result.stdout.lower()
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def _start_ap(self) -> None:
        """Launch balena-wifi-connect in the background."""
        if self._dry_run:
            return
        try:
            subprocess.Popen(
                ["wifi-connect", "--ssid", self.AP_SSID],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            # wifi-connect not installed – log and continue
            logger.warning("wifi-connect not found; skipping AP mode.")

    def _wait_for_connection(self, timeout: int = 300) -> None:
        """Block until connected or timeout (seconds) is reached."""
        if self._dry_run:
            return
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._check_connected():
                return
            time.sleep(self.CHECK_INTERVAL)
