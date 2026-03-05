"""Tests for the OTA update pipeline."""

import json
import stat
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from src import ota as ota_module


FAKE_RELEASE = {
    "tag_name": "v0.2.0",
    "assets": [
        {
            "name": "stemstomp",
            "browser_download_url": "https://example.com/stemstomp",
        }
    ],
}

FAKE_RELEASE_NO_ASSET = {
    "tag_name": "v0.2.0",
    "assets": [],
}


class TestReadLocalVersion:
    def test_reads_version_from_file(self, tmp_path):
        vfile = tmp_path / "version.txt"
        vfile.write_text("v0.1.0\n")
        with patch.object(ota_module, "VERSION_FILE", vfile):
            assert ota_module.read_local_version() == "v0.1.0"

    def test_returns_default_when_file_missing(self, tmp_path):
        missing = tmp_path / "no_version.txt"
        with patch.object(ota_module, "VERSION_FILE", missing):
            assert ota_module.read_local_version() == "v0.0.0"


class TestUpdateAvailable:
    def test_same_version_no_update(self):
        assert ota_module.update_available("v0.1.0", "v0.1.0") is False

    def test_different_version_update_needed(self):
        assert ota_module.update_available("v0.1.0", "v0.2.0") is True

    def test_strips_v_prefix(self):
        assert ota_module.update_available("0.1.0", "v0.1.0") is False

    def test_older_remote_does_not_trigger_update(self):
        # Semver ordering prevents downgrades
        assert ota_module.update_available("v0.2.0", "v0.1.0") is False


class TestFetchLatestRelease:
    def test_returns_parsed_json(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = FAKE_RELEASE
        mock_resp.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_resp) as mock_get:
            result = ota_module.fetch_latest_release()

        assert result["tag_name"] == "v0.2.0"
        mock_get.assert_called_once()

    def test_raises_on_http_error(self):
        import requests

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("404")

        with patch("requests.get", return_value=mock_resp):
            with pytest.raises(requests.HTTPError):
                ota_module.fetch_latest_release()


class TestDownloadAsset:
    def test_returns_false_when_asset_not_found(self, tmp_path):
        dest = tmp_path / "stemstomp"
        result = ota_module.download_asset(FAKE_RELEASE_NO_ASSET, dest)
        assert result is False

    def test_downloads_and_writes_binary(self, tmp_path):
        dest = tmp_path / "stemstomp"
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.iter_content.return_value = [b"fake_binary_data"]

        with patch("requests.get", return_value=mock_resp):
            result = ota_module.download_asset(FAKE_RELEASE, dest)

        assert result is True
        assert dest.exists()
        assert dest.read_bytes() == b"fake_binary_data"
        # Check executable bit
        assert dest.stat().st_mode & stat.S_IXUSR


class TestRunOta:
    def test_no_update_when_versions_match(self, tmp_path):
        vfile = tmp_path / "version.txt"
        vfile.write_text("v0.2.0\n")

        with (
            patch.object(ota_module, "VERSION_FILE", vfile),
            patch.object(
                ota_module, "fetch_latest_release", return_value=FAKE_RELEASE
            ),
        ):
            result = ota_module.run_ota(install_dir=tmp_path)

        assert result is False

    def test_update_installed_when_version_differs(self, tmp_path):
        vfile = tmp_path / "version.txt"
        vfile.write_text("v0.1.0\n")

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.iter_content.return_value = [b"new_binary"]

        with (
            patch.object(ota_module, "VERSION_FILE", vfile),
            patch.object(
                ota_module, "fetch_latest_release", return_value=FAKE_RELEASE
            ),
            patch("requests.get", return_value=mock_resp),
        ):
            result = ota_module.run_ota(install_dir=tmp_path)

        assert result is True
        # version.txt should be updated
        assert vfile.read_text().strip() == "v0.2.0"
