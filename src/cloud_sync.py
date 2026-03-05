"""
Asynchronous cloud synchronisation for StemStomp.

Runs in a background daemon thread so it never blocks the real-time
audio thread.  Communicates with the audio engine via a thread-safe
queue.

Upload:  When a new stem path is placed in the upload queue, it is
         uploaded to S3.

Download: A separate polling loop periodically lists the S3 bucket
          and downloads any objects not already present locally.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger("stemstomp.cloud_sync")

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
    _BOTO_AVAILABLE = True
except ImportError:
    _BOTO_AVAILABLE = False


class CloudSync:
    """
    Manages background upload and download of stems to/from S3.

    Parameters
    ----------
    stems_dir:
        Local directory where stems are stored.
    bucket:
        S3 bucket name.
    prefix:
        Key prefix (folder) inside the bucket (default: "stems/").
    poll_interval:
        Seconds between download-check polls (default: 30).
    on_stem_downloaded:
        Optional callback invoked with the local Path when a stem is
        downloaded.  Called from the sync thread – must be thread-safe.
    dry_run:
        If True, no S3 calls are made (for testing).
    """

    def __init__(
        self,
        stems_dir: Path,
        bucket: str,
        prefix: str = "stems/",
        poll_interval: int = 30,
        on_stem_downloaded: Optional[Callable[[Path], None]] = None,
        dry_run: bool = not _BOTO_AVAILABLE,
    ) -> None:
        self._stems_dir = stems_dir
        self._bucket = bucket
        self._prefix = prefix
        self._poll_interval = poll_interval
        self._on_stem_downloaded = on_stem_downloaded
        self._dry_run = dry_run

        self._upload_queue: queue.Queue[Path] = queue.Queue()
        self._running = False
        self._upload_thread: Optional[threading.Thread] = None
        self._download_thread: Optional[threading.Thread] = None
        self._s3 = None

        if not self._dry_run and _BOTO_AVAILABLE:
            self._s3 = boto3.client("s3")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start background upload and download threads."""
        self._running = True
        self._upload_thread = threading.Thread(
            target=self._upload_loop, daemon=True, name="cloud-upload"
        )
        self._download_thread = threading.Thread(
            target=self._download_loop, daemon=True, name="cloud-download"
        )
        self._upload_thread.start()
        self._download_thread.start()

    def stop(self) -> None:
        """Signal threads to stop and wait for them."""
        self._running = False
        # Unblock upload queue
        self._upload_queue.put_nowait(None)  # type: ignore[arg-type]
        if self._upload_thread:
            self._upload_thread.join(timeout=5)
        if self._download_thread:
            self._download_thread.join(timeout=5)

    def enqueue_upload(self, path: Path) -> None:
        """Add *path* to the upload queue (non-blocking, thread-safe)."""
        self._upload_queue.put_nowait(path)

    # ------------------------------------------------------------------
    # Upload loop
    # ------------------------------------------------------------------

    def _upload_loop(self) -> None:
        while self._running:
            try:
                path = self._upload_queue.get(timeout=1)
            except queue.Empty:
                continue

            if path is None:  # sentinel – stop signal
                break

            self._upload(path)

    def _upload(self, path: Path) -> None:
        if self._dry_run or self._s3 is None:
            return
        key = f"{self._prefix}{path.name}"
        try:
            self._s3.upload_file(str(path), self._bucket, key)
        except (BotoCoreError, ClientError) as exc:
            logger.error("Upload failed for %s: %s", path.name, exc)

    # ------------------------------------------------------------------
    # Download loop
    # ------------------------------------------------------------------

    def _download_loop(self) -> None:
        while self._running:
            self._check_for_new_stems()
            # Sleep in small increments so we can stop promptly
            for _ in range(self._poll_interval * 2):
                if not self._running:
                    return
                time.sleep(0.5)

    def _check_for_new_stems(self) -> None:
        if self._dry_run or self._s3 is None:
            return
        try:
            resp = self._s3.list_objects_v2(
                Bucket=self._bucket, Prefix=self._prefix
            )
        except (BotoCoreError, ClientError) as exc:
            logger.error("List failed: %s", exc)
            return

        for obj in resp.get("Contents", []):
            key: str = obj["Key"]
            filename = key[len(self._prefix):]
            if not filename:
                continue
            local_path = self._stems_dir / filename
            if not local_path.exists():
                self._download(key, local_path)

    def _download(self, key: str, dest: Path) -> None:
        if self._dry_run or self._s3 is None:
            return
        try:
            self._s3.download_file(self._bucket, key, str(dest))
            if self._on_stem_downloaded:
                self._on_stem_downloaded(dest)
        except (BotoCoreError, ClientError) as exc:
            logger.error("Download failed for %s: %s", key, exc)
