"""
GPIO footswitch handler for StemStomp.

Maps physical GPIO pins to logical pedal actions.  The module uses
RPi.GPIO when available; otherwise it operates in *stub mode* for
development / testing on non-Pi hardware.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import Callable, Dict, Optional

try:
    import RPi.GPIO as GPIO
    _GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    _GPIO_AVAILABLE = False


class FootswitchEvent(Enum):
    RECORD_TOGGLE = auto()
    PLAYBACK_TOGGLE = auto()
    SYNC_TRIGGER = auto()


# Default GPIO pin assignments (BCM numbering)
DEFAULT_PIN_MAP: Dict[int, FootswitchEvent] = {
    17: FootswitchEvent.RECORD_TOGGLE,
    27: FootswitchEvent.PLAYBACK_TOGGLE,
    22: FootswitchEvent.SYNC_TRIGGER,
}


class GPIOHandler:
    """
    Registers rising-edge interrupts on footswitch GPIO pins and
    dispatches ``FootswitchEvent`` callbacks.

    Thread-safety: callbacks are invoked from the GPIO interrupt thread.
    The caller is responsible for ensuring callback bodies are
    thread-safe.
    """

    DEBOUNCE_MS = 200

    def __init__(
        self,
        pin_map: Optional[Dict[int, FootswitchEvent]] = None,
        dry_run: bool = not _GPIO_AVAILABLE,
    ) -> None:
        self._pin_map = pin_map if pin_map is not None else DEFAULT_PIN_MAP
        self._dry_run = dry_run
        self._callbacks: Dict[FootswitchEvent, Callable[[], None]] = {}

        if not self._dry_run:
            GPIO.setmode(GPIO.BCM)
            for pin in self._pin_map:
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(
        self, event: FootswitchEvent, callback: Callable[[], None]
    ) -> None:
        """Register *callback* to be called when *event* fires."""
        self._callbacks[event] = callback

        if not self._dry_run:
            for pin, mapped_event in self._pin_map.items():
                if mapped_event == event:
                    GPIO.add_event_detect(
                        pin,
                        GPIO.FALLING,
                        callback=lambda ch, e=event: self._dispatch(e),
                        bouncetime=self.DEBOUNCE_MS,
                    )

    def simulate(self, event: FootswitchEvent) -> None:
        """Programmatically fire an event (used in tests / dry run)."""
        self._dispatch(event)

    def cleanup(self) -> None:
        """Release GPIO resources."""
        if not self._dry_run:
            GPIO.cleanup()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _dispatch(self, event: FootswitchEvent) -> None:
        cb = self._callbacks.get(event)
        if cb is not None:
            cb()
