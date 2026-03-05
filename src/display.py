"""
SSD1306 OLED display manager for StemStomp.

Wraps luma.oled with a simple API that renders the UI states
required by the system state machine.  All draw calls are
thread-safe: a lock is held for the duration of each refresh.
"""

from __future__ import annotations

import logging
import threading
import time
from enum import Enum, auto
from typing import Optional

logger = logging.getLogger("stemstomp.display")

try:
    from luma.core.interface.serial import i2c
    from luma.oled.device import ssd1306
    from PIL import Image, ImageDraw, ImageFont
    _LUMA_AVAILABLE = True
except ImportError:  # running on non-Pi / test environment
    _LUMA_AVAILABLE = False


class DisplayState(Enum):
    BOOTING = auto()
    NO_WIFI = auto()
    AP_MODE = auto()
    PROVISIONING = auto()
    UPDATING = auto()
    RECORDING = auto()
    SYNCING = auto()
    IDLE = auto()
    ERROR = auto()


class OLEDDisplay:
    """
    Manages the SSD1306 128×64 OLED connected via I2C.

    On non-Pi hardware (or when luma.oled is not installed) the class
    operates in *stub mode*: all draw calls are silently ignored, which
    allows the rest of the codebase to run in unit tests without
    physical hardware.
    """

    WIDTH = 128
    HEIGHT = 64

    # States that use the blink flag for animation
    _BLINK_STATES = frozenset({
        DisplayState.SYNCING,
        DisplayState.AP_MODE,
        DisplayState.PROVISIONING,
    })

    def __init__(self, i2c_port: int = 1, i2c_address: int = 0x3C) -> None:
        self._lock = threading.Lock()
        self._state: DisplayState = DisplayState.BOOTING
        self._stem_count: int = 0
        self._blink_visible: bool = True
        self._blink_thread: Optional[threading.Thread] = None
        self._running: bool = False
        self._device = None

        if _LUMA_AVAILABLE:
            try:
                serial = i2c(port=i2c_port, address=i2c_address)
                self._device = ssd1306(serial)
            except Exception as exc:  # pragma: no cover
                # Hardware not present (e.g., development machine)
                logger.warning("OLED init failed (%s); running in stub mode.", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the display and background blink thread."""
        self._running = True
        self._blink_thread = threading.Thread(target=self._blink_loop, daemon=True)
        self._blink_thread.start()
        self.set_state(DisplayState.BOOTING)

    def stop(self) -> None:
        """Stop background threads and blank the display."""
        self._running = False
        if self._blink_thread:
            self._blink_thread.join(timeout=2)
        if self._device:
            self._device.cleanup()  # pragma: no cover

    def set_state(self, state: DisplayState, stem_count: int = 0) -> None:
        with self._lock:
            self._state = state
            self._stem_count = stem_count
        self._refresh()

    def set_stem_count(self, count: int) -> None:
        with self._lock:
            self._stem_count = count
        self._refresh()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _blink_loop(self) -> None:
        """Toggle blink flag at ~2 Hz for animated states."""
        while self._running:
            time.sleep(0.25)
            with self._lock:
                self._blink_visible = not self._blink_visible
            if self._state in self._BLINK_STATES:
                self._refresh()

    def _refresh(self) -> None:
        """Re-render the current state to the display."""
        if self._device is None:
            return  # stub mode

        with self._lock:
            state = self._state
            stem_count = self._stem_count
            blink = self._blink_visible

        image = Image.new("1", (self.WIDTH, self.HEIGHT), 0)
        draw = ImageDraw.Draw(image)

        try:
            font = ImageFont.load_default()
        except Exception:  # pragma: no cover
            font = None

        self._render(draw, state, stem_count, blink, font)
        self._device.display(image)

    @staticmethod
    def _render(
        draw: "ImageDraw.ImageDraw",
        state: DisplayState,
        stem_count: int,
        blink: bool,
        font,
    ) -> None:
        """
        Stateless render function – separated for easy unit-testing.
        All coordinates are for a 128×64 pixel canvas.
        """
        W, H = 128, 64

        if state == DisplayState.BOOTING:
            draw.text((2, 2), "StemStomp", font=font, fill=1)
            draw.text((2, 20), "Booting...", font=font, fill=1)

        elif state == DisplayState.NO_WIFI:
            draw.text((2, 2), "No Wi-Fi", font=font, fill=1)
            draw.text((2, 20), "Check network", font=font, fill=1)

        elif state == DisplayState.AP_MODE:
            draw.text((2, 2), "Setup Mode", font=font, fill=1)
            draw.text((2, 16), "StemStomp-Setup", font=font, fill=1)
            # Blinking indicator
            if blink:
                draw.ellipse((W - 14, 2, W - 2, 14), outline=1)

        elif state == DisplayState.PROVISIONING:
            draw.text((2, 2), "Provisioning...", font=font, fill=1)
            if blink:
                draw.text((2, 20), "Connecting", font=font, fill=1)

        elif state == DisplayState.UPDATING:
            draw.text((2, 2), "Updating...", font=font, fill=1)
            draw.rectangle((2, 20, W - 2, 32), outline=1)

        elif state == DisplayState.RECORDING:
            draw.text((2, 2), "● REC", font=font, fill=1)
            draw.text((2, 20), f"Stems: {stem_count}", font=font, fill=1)
            # Solid recording circle
            draw.ellipse((W - 16, 2, W - 2, 16), fill=1)

        elif state == DisplayState.SYNCING:
            draw.text((2, 2), f"Stems: {stem_count}", font=font, fill=1)
            # Flashing sync arrow (simple representation)
            if blink:
                draw.text((2, 20), "↑ Syncing", font=font, fill=1)
            else:
                draw.text((2, 20), "  Syncing", font=font, fill=1)

        elif state == DisplayState.IDLE:
            draw.text((2, 2), "StemStomp", font=font, fill=1)
            draw.text((2, 20), f"Stems: {stem_count}", font=font, fill=1)
            draw.text((2, 40), "Ready", font=font, fill=1)

        elif state == DisplayState.ERROR:
            draw.text((2, 2), "ERROR", font=font, fill=1)
            draw.text((2, 20), "Check logs", font=font, fill=1)
