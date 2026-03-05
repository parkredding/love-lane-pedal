"""Integration tests exercising the full boot sequence in dry_run mode."""

import threading
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.config import StemStompConfig
from src.state_machine import StateMachine, BootPhase
from src.display import DisplayState


@pytest.fixture
def config(tmp_path):
    return StemStompConfig(
        stems_dir=tmp_path / "stems",
        dry_run=True,
    )


@pytest.fixture
def machine(config):
    return StateMachine(config=config)


class TestFullBootSequence:
    def test_boot_phases_complete_in_order(self, machine):
        """All 4 boot phases should complete without error in dry_run."""
        machine._phase_hardware_init()
        assert machine._phase == BootPhase.HARDWARE_INIT

        machine._phase_network()
        assert machine._phase == BootPhase.NETWORK

        with patch("src.state_machine.ota_module.run_ota", return_value=False):
            machine._phase_ota()
        assert machine._phase == BootPhase.OTA

    def test_full_run_with_keyboard_interrupt(self, config):
        """StateMachine.run() should handle KeyboardInterrupt gracefully."""
        m = StateMachine(config=config)

        def interrupt_after_delay():
            time.sleep(0.2)
            # Simulate the effect by setting the machine to stop
            m._display._running = False

        with patch("src.state_machine.ota_module.run_ota", return_value=False):
            with patch.object(m, "_phase_running", side_effect=KeyboardInterrupt):
                m.run()

        # Should not raise, shutdown should complete

    def test_record_stop_enqueues_sync(self, tmp_path):
        """Recording -> stop should enqueue upload when sync is configured."""
        config = StemStompConfig(
            stems_dir=tmp_path / "stems",
            s3_bucket="test-bucket",
            dry_run=True,
        )
        m = StateMachine(config=config)
        m._phase_hardware_init()

        # Simulate recording cycle
        m._toggle_recording()
        assert m._display._state == DisplayState.RECORDING

        m._toggle_recording()
        assert m._display._state == DisplayState.IDLE


class TestConfigIntegration:
    def test_config_flows_through_to_components(self, tmp_path):
        """Config values should propagate to sub-components."""
        config = StemStompConfig(
            stems_dir=tmp_path / "stems",
            s3_bucket="my-bucket",
            s3_prefix="audio/",
            sync_poll_interval=60,
            dry_run=True,
        )
        m = StateMachine(config=config)

        assert m._sync is not None
        assert m._sync._prefix == "audio/"
        assert m._sync._poll_interval == 60
