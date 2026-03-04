"""Tests for the SSD1306 OLED display module."""

import threading
from unittest.mock import MagicMock, patch

import pytest

from src.display import DisplayState, OLEDDisplay


@pytest.fixture
def display():
    """Return a stub-mode OLEDDisplay (no hardware required)."""
    d = OLEDDisplay()
    # _device is None in stub mode – no hardware calls
    assert d._device is None
    return d


class TestDisplayStateTransitions:
    def test_initial_state_is_booting(self, display):
        assert display._state == DisplayState.BOOTING

    def test_set_state_updates_state(self, display):
        display.set_state(DisplayState.IDLE)
        assert display._state == DisplayState.IDLE

    def test_set_stem_count_updates_count(self, display):
        display.set_state(DisplayState.IDLE, stem_count=3)
        assert display._stem_count == 3

    def test_all_display_states_accepted(self, display):
        for state in DisplayState:
            display.set_state(state)
            assert display._state == state

    def test_start_and_stop(self, display):
        display.start()
        assert display._running is True
        display.stop()
        assert display._running is False


class TestRenderFunction:
    """Test the stateless _render function directly (no hardware)."""

    @pytest.fixture
    def canvas(self):
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            pytest.skip("Pillow not installed")
        image = Image.new("1", (128, 64), 0)
        draw = ImageDraw.Draw(image)
        return draw

    def _render(self, canvas, state, stem_count=0, blink=True):
        OLEDDisplay._render(canvas, state, stem_count, blink, font=None)

    def test_render_booting(self, canvas):
        self._render(canvas, DisplayState.BOOTING)

    def test_render_recording_shows_rec(self, canvas):
        self._render(canvas, DisplayState.RECORDING, stem_count=2)

    def test_render_syncing_with_blink_on(self, canvas):
        self._render(canvas, DisplayState.SYNCING, stem_count=1, blink=True)

    def test_render_syncing_with_blink_off(self, canvas):
        self._render(canvas, DisplayState.SYNCING, stem_count=1, blink=False)

    def test_render_ap_mode(self, canvas):
        self._render(canvas, DisplayState.AP_MODE)

    def test_render_idle(self, canvas):
        self._render(canvas, DisplayState.IDLE, stem_count=5)

    def test_render_error(self, canvas):
        self._render(canvas, DisplayState.ERROR)

    def test_render_no_wifi(self, canvas):
        self._render(canvas, DisplayState.NO_WIFI)


class TestThreadSafety:
    def test_concurrent_set_state(self, display):
        """Multiple threads calling set_state should not raise."""
        errors = []

        def set_states():
            try:
                for state in list(DisplayState):
                    display.set_state(state)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=set_states) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
