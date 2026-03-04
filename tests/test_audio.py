"""Tests for the audio engine."""

import numpy as np
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.audio import AudioEngine, SAMPLE_RATE, CHANNELS, DTYPE, SUBTYPE


@pytest.fixture
def stems_dir(tmp_path):
    return tmp_path / "stems"


@pytest.fixture
def engine(stems_dir):
    """Return an AudioEngine in dry_run mode."""
    return AudioEngine(stems_dir=stems_dir, dry_run=True)


class TestAudioEngineDryRun:
    def test_initial_state(self, engine):
        assert engine.is_recording is False
        assert engine.is_playing is False

    def test_start_recording_does_not_raise(self, engine):
        engine.start_recording()
        # In dry_run mode, the recording flag IS set (state tracked without hardware)
        assert engine.is_recording is True

    def test_stop_recording_returns_none_in_dry_run(self, engine):
        result = engine.stop_recording()
        assert result is None

    def test_load_stems_returns_zero_in_dry_run(self, engine):
        count = engine.load_stems()
        assert count == 0

    def test_stem_count_returns_zero_for_empty_dir(self, engine):
        assert engine.stem_count == 0

    def test_cleanup_does_not_raise(self, engine):
        engine.cleanup()


class TestStemCount:
    def test_stem_count_reflects_wav_files(self, stems_dir):
        stems_dir.mkdir(parents=True)
        (stems_dir / "stem_1.wav").write_bytes(b"")
        (stems_dir / "stem_2.wav").write_bytes(b"")
        engine = AudioEngine(stems_dir=stems_dir, dry_run=True)
        assert engine.stem_count == 2

    def test_stem_count_ignores_non_wav(self, stems_dir):
        stems_dir.mkdir(parents=True)
        (stems_dir / "notes.txt").write_text("hello")
        engine = AudioEngine(stems_dir=stems_dir, dry_run=True)
        assert engine.stem_count == 0


class TestOnRecordingSavedCallback:
    def test_callback_invoked_after_stop_recording(self, stems_dir):
        """When sounddevice is available, saving a stem should fire the callback."""
        try:
            import sounddevice  # noqa: F401
            import soundfile  # noqa: F401
        except (ImportError, OSError):
            pytest.skip("sounddevice/soundfile not installed")

        called_paths = []
        engine = AudioEngine(
            stems_dir=stems_dir,
            on_recording_saved=lambda p: called_paths.append(p),
            dry_run=False,
        )

        # Manually inject data into the rec buffer instead of opening a stream
        engine._recording = True
        engine._rec_buffer.append(
            np.zeros((SAMPLE_RATE, CHANNELS), dtype=DTYPE)
        )

        result = engine.stop_recording()
        assert result is not None
        assert result.exists()
        assert called_paths == [result]


class TestPlaybackMixing:
    def test_playback_callback_mixes_stems(self, stems_dir):
        """The playback callback should sum multiple stems without overflow."""
        engine = AudioEngine(stems_dir=stems_dir, dry_run=False)

        # Two constant-value stems
        data_a = np.full((100, CHANNELS), 1000, dtype=DTYPE)
        data_b = np.full((100, CHANNELS), 2000, dtype=DTYPE)
        engine._playback_data = [data_a, data_b]
        engine._playback_pos = [0, 0]

        outdata = np.zeros((100, CHANNELS), dtype=DTYPE)

        # Simulate the callback (without sd.CallbackStop)
        try:
            engine._playback_callback(outdata, 100, None, None)
        except Exception:
            pass  # CallbackStop is expected when data is exhausted

        # Mixed value should be 3000 for each frame
        assert (outdata[:, 0] == 3000).all()
