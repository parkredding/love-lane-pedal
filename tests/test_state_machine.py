"""Integration-level tests for the StateMachine."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import threading

import pytest

from src.state_machine import StateMachine, BootPhase
from src.display import DisplayState
from src.network import NetworkState


@pytest.fixture
def machine(tmp_path):
    """Return a StateMachine in dry_run mode with a temporary stems dir."""
    return StateMachine(stems_dir=tmp_path / "stems", dry_run=True)


class TestStateMachineBootPhases:
    def test_hardware_init_sets_booting_state(self, machine):
        machine._phase_hardware_init()
        assert machine._phase == BootPhase.HARDWARE_INIT
        assert machine._display._state == DisplayState.BOOTING

    def test_ota_phase_handles_network_error_gracefully(self, machine):
        """OTA errors must not raise – they are non-fatal."""
        with patch("src.state_machine.ota_module.run_ota", side_effect=Exception("timeout")):
            machine._phase_hardware_init()
            machine._phase_ota()
        # Should still be running
        assert machine._phase == BootPhase.OTA

    def test_network_phase_dry_run_skips_wifi_check(self, machine):
        """In dry_run mode the network phase completes without raising."""
        machine._phase_hardware_init()
        # Should not raise – dry_run bypasses real connectivity checks
        machine._phase_network()

    def test_toggle_recording_changes_display_state(self, machine):
        machine._phase_hardware_init()
        # Start recording
        machine._toggle_recording()
        assert machine._display._state == DisplayState.RECORDING
        # Stop recording
        machine._toggle_recording()
        assert machine._display._state == DisplayState.IDLE

    def test_toggle_playback_changes_display_state(self, machine):
        machine._phase_hardware_init()
        # Start – no stems loaded, audio is dry_run so start_playback is a no-op
        machine._toggle_playback()
        assert machine._display._state == DisplayState.IDLE

    def test_recording_saved_enqueues_sync_upload(self, tmp_path):
        m = StateMachine(
            stems_dir=tmp_path / "stems",
            s3_bucket="test-bucket",
            dry_run=True,
        )
        m._phase_hardware_init()
        stem = tmp_path / "stems" / "stem_1.wav"
        stem.parent.mkdir(parents=True, exist_ok=True)
        stem.write_bytes(b"")
        m._on_recording_saved(stem)
        # Queue should have one item
        assert not m._sync._upload_queue.empty()

    def test_shutdown_does_not_raise(self, machine):
        machine._phase_hardware_init()
        machine._shutdown()
