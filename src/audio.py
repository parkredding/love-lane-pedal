"""
Real-time audio engine for StemStomp.

Records 24-bit / 44.1 kHz audio from the input device into WAV files
and plays back multiple stems simultaneously.  Uses ``sounddevice``
for low-latency I/O and ``soundfile`` for WAV encoding.

Recording and playback run on the real-time audio thread;  all
filesystem I/O (writing the final WAV) is done synchronously inside
the recording stop handler – still on the audio thread – but is fast
enough for the stem sizes involved.  Cloud sync is performed on a
completely separate thread (see cloud_sync.py).
"""

from __future__ import annotations

import queue
import threading
import time
from pathlib import Path
from typing import Callable, List, Optional

import numpy as np

try:
    import sounddevice as sd
    import soundfile as sf
    _AUDIO_AVAILABLE = True
except (ImportError, OSError):
    _AUDIO_AVAILABLE = False


SAMPLE_RATE = 44100
CHANNELS = 1
DTYPE = "int32"          # 32-bit container for 24-bit audio
BLOCK_SIZE = 1024        # frames per callback (~23 ms latency)
SUBTYPE = "PCM_24"       # WAV sub-type for 24-bit depth


class AudioEngine:
    """
    Manages recording and multi-track playback of WAV stems.

    In stub mode (no sounddevice / ALSA) all operations are silently
    no-ops so tests can run on any platform.
    """

    def __init__(
        self,
        stems_dir: Path,
        on_recording_saved: Optional[Callable[[Path], None]] = None,
        dry_run: bool = not _AUDIO_AVAILABLE,
    ) -> None:
        self._stems_dir = stems_dir
        self._stems_dir.mkdir(parents=True, exist_ok=True)
        self._on_recording_saved = on_recording_saved
        self._dry_run = dry_run

        self._recording = False
        self._playing = False
        self._rec_buffer: List[np.ndarray] = []
        self._rec_lock = threading.Lock()
        self._input_stream: Optional["sd.InputStream"] = None
        self._output_stream: Optional["sd.OutputStream"] = None
        self._playback_data: List[np.ndarray] = []
        self._playback_pos: List[int] = []

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start_recording(self) -> None:
        """Begin capturing audio from the default input device."""
        if self._recording:
            return
        self._recording = True
        if self._dry_run:
            return
        self._input_stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=BLOCK_SIZE,
            callback=self._record_callback,
        )
        self._input_stream.start()

    def stop_recording(self) -> Optional[Path]:
        """
        Stop recording and save the captured audio to a WAV file.

        Returns the path of the saved file, or None in stub mode.
        """
        if not self._recording:
            return None
        self._recording = False
        if self._dry_run:
            return None
        if self._input_stream:
            self._input_stream.stop()
            self._input_stream.close()
            self._input_stream = None

        with self._rec_lock:
            if self._rec_buffer:
                data = np.concatenate(self._rec_buffer, axis=0)
            else:
                data = np.zeros((0, CHANNELS), dtype=DTYPE)
            self._rec_buffer.clear()

        stem_path = self._stems_dir / f"stem_{int(time.time())}.wav"
        sf.write(str(stem_path), data, SAMPLE_RATE, subtype=SUBTYPE)

        if self._on_recording_saved:
            self._on_recording_saved(stem_path)

        return stem_path

    def _record_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info,
        status,
    ) -> None:
        with self._rec_lock:
            self._rec_buffer.append(indata.copy())

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------

    @property
    def is_playing(self) -> bool:
        return self._playing

    def load_stems(self) -> int:
        """
        Load all WAV files from the stems directory into memory.

        Returns the number of stems loaded.
        """
        self._playback_data.clear()
        self._playback_pos.clear()

        if self._dry_run:
            return 0

        for wav_path in sorted(self._stems_dir.glob("*.wav")):
            data, sr = sf.read(str(wav_path), dtype=DTYPE, always_2d=True)
            if sr != SAMPLE_RATE:
                # Skip stems with a mismatched sample rate
                continue
            self._playback_data.append(data)
            self._playback_pos.append(0)

        return len(self._playback_data)

    def start_playback(self) -> None:
        """Begin simultaneous playback of all loaded stems."""
        if self._dry_run or self._playing or not self._playback_data:
            return
        self._playing = True
        self._playback_pos = [0] * len(self._playback_data)
        self._output_stream = sd.OutputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=BLOCK_SIZE,
            callback=self._playback_callback,
            finished_callback=self._playback_finished,
        )
        self._output_stream.start()

    def stop_playback(self) -> None:
        """Stop playback immediately."""
        if self._dry_run or not self._playing:
            return
        self._playing = False
        if self._output_stream:
            self._output_stream.stop()
            self._output_stream.close()
            self._output_stream = None

    def _playback_callback(
        self,
        outdata: np.ndarray,
        frames: int,
        time_info,
        status,
    ) -> None:
        """Mix all stems together and write to output buffer."""
        mixed = np.zeros((frames, CHANNELS), dtype=np.int64)
        all_done = True

        for i, data in enumerate(self._playback_data):
            pos = self._playback_pos[i]
            remaining = len(data) - pos
            if remaining <= 0:
                continue
            all_done = False
            chunk_len = min(frames, remaining)
            mixed[:chunk_len] += data[pos : pos + chunk_len].astype(np.int64)
            self._playback_pos[i] = pos + chunk_len

        # Clip to int32 range to prevent overflow
        np.clip(mixed, np.iinfo(np.int32).min, np.iinfo(np.int32).max, out=mixed)
        outdata[:] = mixed.astype(np.int32)

        if all_done:
            self._playing = False
            raise sd.CallbackStop()

    def _playback_finished(self) -> None:
        self._playing = False

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @property
    def stem_count(self) -> int:
        """Return the number of WAV files in the stems directory."""
        return len(list(self._stems_dir.glob("*.wav")))

    def cleanup(self) -> None:
        """Stop all streams and release resources."""
        self.stop_recording()
        self.stop_playback()
