"""Tests for the GPIO footswitch handler."""

import pytest

from src.gpio_handler import FootswitchEvent, GPIOHandler


@pytest.fixture
def handler():
    """Return a GPIOHandler in dry_run mode (no RPi.GPIO calls)."""
    return GPIOHandler(dry_run=True)


class TestGPIOHandlerDryRun:
    def test_register_and_simulate_event(self, handler):
        called = []
        handler.register(FootswitchEvent.RECORD_TOGGLE, lambda: called.append(True))
        handler.simulate(FootswitchEvent.RECORD_TOGGLE)
        assert called == [True]

    def test_simulate_unregistered_event_does_not_raise(self, handler):
        # No callback registered – should silently do nothing
        handler.simulate(FootswitchEvent.PLAYBACK_TOGGLE)

    def test_each_event_fires_its_own_callback(self, handler):
        record_calls = []
        play_calls = []
        handler.register(
            FootswitchEvent.RECORD_TOGGLE, lambda: record_calls.append(1)
        )
        handler.register(
            FootswitchEvent.PLAYBACK_TOGGLE, lambda: play_calls.append(1)
        )

        handler.simulate(FootswitchEvent.RECORD_TOGGLE)
        handler.simulate(FootswitchEvent.PLAYBACK_TOGGLE)
        handler.simulate(FootswitchEvent.RECORD_TOGGLE)

        assert record_calls == [1, 1]
        assert play_calls == [1]

    def test_cleanup_does_not_raise(self, handler):
        handler.cleanup()

    def test_register_overwrites_previous_callback(self, handler):
        calls_a = []
        calls_b = []
        handler.register(
            FootswitchEvent.SYNC_TRIGGER, lambda: calls_a.append("a")
        )
        handler.register(
            FootswitchEvent.SYNC_TRIGGER, lambda: calls_b.append("b")
        )
        handler.simulate(FootswitchEvent.SYNC_TRIGGER)
        # Only the latest callback should fire
        assert calls_a == []
        assert calls_b == ["b"]
