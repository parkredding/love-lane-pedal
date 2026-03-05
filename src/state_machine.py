"""
Core boot state machine for StemStomp.

Implements the strict linear boot sequence described in the spec:

  1. Hardware Init  (OLED "Booting...")
  2. Network Resolution  (connect or captive portal)
  3. OTA Firmware Check  (GitHub API)
  4. Main Application Launch  (audio engine + cloud sync)

Each phase updates the OLED so the user always knows what is
happening even though there is no monitor.
"""

from __future__ import annotations

import logging
from enum import Enum, auto
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from .display import OLEDDisplay, DisplayState
from .network import NetworkManager, NetworkState
from . import ota as ota_module
from .audio import AudioEngine
from .cloud_sync import CloudSync
from .gpio_handler import GPIOHandler, FootswitchEvent

if TYPE_CHECKING:
    from .config import StemStompConfig

logger = logging.getLogger("stemstomp.state_machine")


class BootPhase(Enum):
    HARDWARE_INIT = auto()
    NETWORK = auto()
    OTA = auto()
    RUNNING = auto()
    ERROR = auto()


class StateMachine:
    """
    Orchestrates the full boot and runtime life-cycle of StemStomp.

    Accepts either a ``StemStompConfig`` object or the legacy keyword
    arguments for backward compatibility with existing tests.
    """

    def __init__(
        self,
        config: Optional[StemStompConfig] = None,
        *,
        stems_dir: Optional[Path] = None,
        s3_bucket: str = "",
        dry_run: bool = False,
    ) -> None:
        if config is not None:
            stems_dir = config.stems_dir
            s3_bucket = config.s3_bucket
            dry_run = config.dry_run
        elif stems_dir is None:
            stems_dir = Path(__file__).resolve().parent.parent / "stems"

        self._dry_run = dry_run
        self._phase = BootPhase.HARDWARE_INIT

        i2c_port = config.oled_i2c_port if config else 1
        i2c_address = config.oled_i2c_address if config else 0x3C
        self._display = OLEDDisplay(i2c_port=i2c_port, i2c_address=i2c_address)
        self._network = NetworkManager(dry_run=dry_run)
        self._audio = AudioEngine(
            stems_dir=stems_dir,
            on_recording_saved=self._on_recording_saved,
            dry_run=dry_run,
        )

        pin_map = None
        if config is not None:
            pin_map = {
                config.gpio_pin_record: FootswitchEvent.RECORD_TOGGLE,
                config.gpio_pin_playback: FootswitchEvent.PLAYBACK_TOGGLE,
                config.gpio_pin_sync: FootswitchEvent.SYNC_TRIGGER,
            }
        self._gpio = GPIOHandler(pin_map=pin_map, dry_run=dry_run)
        self._sync: Optional[CloudSync] = None

        if s3_bucket:
            prefix = config.s3_prefix if config else "stems/"
            poll_interval = config.sync_poll_interval if config else 30
            self._sync = CloudSync(
                stems_dir=stems_dir,
                bucket=s3_bucket,
                prefix=prefix,
                poll_interval=poll_interval,
                on_stem_downloaded=self._on_stem_downloaded,
                dry_run=dry_run,
            )

    # ------------------------------------------------------------------
    # Boot sequence
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Execute the boot sequence then enter the runtime loop."""
        try:
            self._phase_hardware_init()
            self._phase_network()
            self._phase_ota()
            self._phase_running()
        except KeyboardInterrupt:
            pass
        except Exception as exc:
            self._display.set_state(DisplayState.ERROR)
            logger.error("Fatal error: %s", exc)
        finally:
            self._shutdown()

    # ------------------------------------------------------------------
    # Boot phases
    # ------------------------------------------------------------------

    def _phase_hardware_init(self) -> None:
        self._phase = BootPhase.HARDWARE_INIT
        self._display.start()
        self._display.set_state(DisplayState.BOOTING)

    def _phase_network(self) -> None:
        self._phase = BootPhase.NETWORK
        self._display.set_state(DisplayState.NO_WIFI)

        net_state = self._network.resolve()

        if net_state == NetworkState.AP_MODE:
            self._display.set_state(DisplayState.AP_MODE)
        elif net_state == NetworkState.PROVISIONING:
            self._display.set_state(DisplayState.PROVISIONING)

        # resolve() blocks until connected (or timed out)
        if net_state not in (NetworkState.CONNECTED,) and not self._dry_run:
            raise RuntimeError("Unable to connect to Wi-Fi")

    def _phase_ota(self) -> None:
        self._phase = BootPhase.OTA
        try:
            self._display.set_state(DisplayState.UPDATING)
            updated = ota_module.run_ota()
            if not updated:
                # No update – show idle briefly before audio launch
                pass
        except Exception as exc:
            # OTA failures are non-fatal; log and continue
            logger.warning("OTA check failed: %s", exc)

    def _phase_running(self) -> None:
        self._phase = BootPhase.RUNNING

        # Load existing stems and start cloud sync
        count = self._audio.load_stems()
        self._display.set_state(DisplayState.IDLE, stem_count=count)

        if self._sync:
            self._sync.start()

        # Register footswitch callbacks
        self._gpio.register(FootswitchEvent.RECORD_TOGGLE, self._toggle_recording)
        self._gpio.register(FootswitchEvent.PLAYBACK_TOGGLE, self._toggle_playback)

        # Block until KeyboardInterrupt (real device runs forever)
        import time
        while True:
            time.sleep(1)
            # Refresh stem count periodically
            self._display.set_stem_count(self._audio.stem_count)

    # ------------------------------------------------------------------
    # Runtime event handlers
    # ------------------------------------------------------------------

    def _toggle_recording(self) -> None:
        if self._audio.is_recording:
            self._audio.stop_recording()
            self._display.set_state(
                DisplayState.IDLE, stem_count=self._audio.stem_count
            )
        else:
            self._audio.start_recording()
            self._display.set_state(
                DisplayState.RECORDING, stem_count=self._audio.stem_count
            )

    def _toggle_playback(self) -> None:
        if self._audio.is_playing:
            self._audio.stop_playback()
            self._display.set_state(
                DisplayState.IDLE, stem_count=self._audio.stem_count
            )
        else:
            self._audio.load_stems()
            self._audio.start_playback()
            self._display.set_state(
                DisplayState.IDLE, stem_count=self._audio.stem_count
            )

    def _on_recording_saved(self, path: Path) -> None:
        """Called from audio thread when a new stem is written to disk."""
        if self._sync:
            self._sync.enqueue_upload(path)
            self._display.set_state(
                DisplayState.SYNCING, stem_count=self._audio.stem_count
            )

    def _on_stem_downloaded(self, path: Path) -> None:
        """Called from sync thread when a new stem is downloaded."""
        self._display.set_state(
            DisplayState.SYNCING, stem_count=self._audio.stem_count
        )

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def _shutdown(self) -> None:
        if self._sync:
            self._sync.stop()
        self._audio.cleanup()
        self._gpio.cleanup()
        self._display.stop()
