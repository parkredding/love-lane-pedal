"""Tests for the configuration module."""

import os
from pathlib import Path

import pytest

from src.config import StemStompConfig, _load_env_file


class TestLoadEnvFile:
    def test_parses_key_value(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("FOO=bar\nBAZ=qux\n")
        result = _load_env_file(env_file)
        assert result == {"FOO": "bar", "BAZ": "qux"}

    def test_ignores_comments_and_blanks(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("# comment\n\nFOO=bar\n")
        result = _load_env_file(env_file)
        assert result == {"FOO": "bar"}

    def test_returns_empty_for_missing_file(self, tmp_path):
        result = _load_env_file(tmp_path / "missing")
        assert result == {}


class TestStemStompConfig:
    def test_defaults(self):
        config = StemStompConfig()
        assert config.s3_bucket == ""
        assert config.dry_run is False
        assert config.gpio_pin_record == 17
        assert config.oled_i2c_address == 0x3C
        assert config.log_level == "INFO"

    def test_load_from_env_vars(self, monkeypatch, tmp_path):
        monkeypatch.setenv("STEMSTOMP_S3_BUCKET", "test-bucket")
        monkeypatch.setenv("STEMSTOMP_DRY_RUN", "1")
        monkeypatch.setenv("STEMSTOMP_STEMS_DIR", str(tmp_path))
        monkeypatch.setenv("STEMSTOMP_LOG_LEVEL", "DEBUG")

        config = StemStompConfig.load(env_file=tmp_path / "nonexistent")
        assert config.s3_bucket == "test-bucket"
        assert config.dry_run is True
        assert config.stems_dir == tmp_path
        assert config.log_level == "DEBUG"

    def test_load_from_env_file(self, tmp_path, monkeypatch):
        # Clear any existing env vars
        for key in list(os.environ):
            if key.startswith("STEMSTOMP_"):
                monkeypatch.delenv(key, raising=False)

        env_file = tmp_path / ".env"
        env_file.write_text("STEMSTOMP_S3_BUCKET=file-bucket\nSTEMSTOMP_GPIO_RECORD=18\n")

        config = StemStompConfig.load(env_file=env_file)
        assert config.s3_bucket == "file-bucket"
        assert config.gpio_pin_record == 18

    def test_env_vars_override_file(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("STEMSTOMP_S3_BUCKET=file-bucket\n")
        monkeypatch.setenv("STEMSTOMP_S3_BUCKET", "env-bucket")

        config = StemStompConfig.load(env_file=env_file)
        assert config.s3_bucket == "env-bucket"

    def test_hex_oled_address(self, tmp_path, monkeypatch):
        for key in list(os.environ):
            if key.startswith("STEMSTOMP_"):
                monkeypatch.delenv(key, raising=False)
        env_file = tmp_path / ".env"
        env_file.write_text("STEMSTOMP_OLED_ADDRESS=0x3D\n")

        config = StemStompConfig.load(env_file=env_file)
        assert config.oled_i2c_address == 0x3D
