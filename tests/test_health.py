"""Tests for the health check module."""

import json
from pathlib import Path

import pytest

from src.health import HealthCheck


@pytest.fixture
def health(tmp_path):
    version_file = tmp_path / "version.txt"
    version_file.write_text("v0.1.0\n")
    stems_dir = tmp_path / "stems"
    stems_dir.mkdir()
    return HealthCheck(stems_dir=stems_dir, version_file=version_file)


class TestHealthCheck:
    def test_collect_returns_dict(self, health):
        result = health.collect()
        assert isinstance(result, dict)
        assert result["version"] == "v0.1.0"
        assert result["stem_count"] == 0
        assert result["uptime_seconds"] >= 0
        assert result["disk_free_mb"] >= 0

    def test_stem_count(self, health, tmp_path):
        stems_dir = tmp_path / "stems"
        (stems_dir / "stem_1.wav").write_bytes(b"")
        (stems_dir / "stem_2.wav").write_bytes(b"")
        result = health.collect()
        assert result["stem_count"] == 2

    def test_write_status(self, health, tmp_path):
        status_file = tmp_path / "health.json"
        health.write_status(status_file)
        assert status_file.exists()
        data = json.loads(status_file.read_text())
        assert "version" in data

    def test_missing_version_file(self, tmp_path):
        h = HealthCheck(
            stems_dir=tmp_path / "stems",
            version_file=tmp_path / "missing.txt",
        )
        result = h.collect()
        assert result["version"] == "unknown"
