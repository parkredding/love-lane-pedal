"""Tests for the cloud sync module."""

import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from src.cloud_sync import CloudSync


@pytest.fixture
def stems_dir(tmp_path):
    d = tmp_path / "stems"
    d.mkdir()
    return d


@pytest.fixture
def sync(stems_dir):
    """Return a CloudSync in dry_run mode."""
    return CloudSync(stems_dir=stems_dir, bucket="test-bucket", dry_run=True)


class TestCloudSyncDryRun:
    def test_enqueue_upload_does_not_raise(self, sync, stems_dir):
        p = stems_dir / "stem_1.wav"
        p.write_bytes(b"")
        sync.enqueue_upload(p)

    def test_start_and_stop(self, sync):
        sync.start()
        assert sync._running is True
        sync.stop()
        assert sync._running is False

    def test_upload_noop_in_dry_run(self, sync, stems_dir):
        p = stems_dir / "stem.wav"
        p.write_bytes(b"")
        # Should complete without raising
        sync._upload(p)

    def test_check_for_new_stems_noop_in_dry_run(self, sync):
        sync._check_for_new_stems()  # should not raise


class TestCloudSyncWithMockedS3:
    def test_upload_calls_s3_upload_file(self, stems_dir):
        mock_s3 = MagicMock()
        sync = CloudSync(
            stems_dir=stems_dir, bucket="my-bucket", prefix="stems/", dry_run=False
        )
        sync._s3 = mock_s3

        stem = stems_dir / "stem_001.wav"
        stem.write_bytes(b"audio")
        sync._upload(stem)

        mock_s3.upload_file.assert_called_once_with(
            str(stem), "my-bucket", "stems/stem_001.wav"
        )

    def test_download_called_for_new_remote_stems(self, stems_dir):
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "stems/new_stem.wav"},
            ]
        }
        downloaded = []
        sync = CloudSync(
            stems_dir=stems_dir,
            bucket="my-bucket",
            prefix="stems/",
            on_stem_downloaded=lambda p: downloaded.append(p),
            dry_run=False,
        )
        sync._s3 = mock_s3
        sync._check_for_new_stems()

        mock_s3.download_file.assert_called_once_with(
            "my-bucket",
            "stems/new_stem.wav",
            str(stems_dir / "new_stem.wav"),
        )
        assert downloaded == [stems_dir / "new_stem.wav"]

    def test_existing_stems_not_re_downloaded(self, stems_dir):
        existing = stems_dir / "existing.wav"
        existing.write_bytes(b"")

        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [{"Key": "stems/existing.wav"}]
        }
        sync = CloudSync(
            stems_dir=stems_dir,
            bucket="my-bucket",
            prefix="stems/",
            dry_run=False,
        )
        sync._s3 = mock_s3
        sync._check_for_new_stems()

        mock_s3.download_file.assert_not_called()

    def test_upload_error_does_not_propagate(self, stems_dir):
        try:
            from botocore.exceptions import ClientError
        except ImportError:
            pytest.skip("botocore not installed")

        mock_s3 = MagicMock()
        mock_s3.upload_file.side_effect = ClientError(
            {"Error": {"Code": "NoSuchBucket", "Message": ""}}, "upload_file"
        )
        sync = CloudSync(
            stems_dir=stems_dir, bucket="bad-bucket", dry_run=False
        )
        sync._s3 = mock_s3

        stem = stems_dir / "stem.wav"
        stem.write_bytes(b"")
        # Should not raise
        sync._upload(stem)
