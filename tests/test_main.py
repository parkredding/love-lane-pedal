"""Tests for the main entry point."""

from unittest.mock import patch, MagicMock

import pytest


class TestMain:
    def test_main_constructs_state_machine(self, monkeypatch):
        monkeypatch.setenv("STEMSTOMP_DRY_RUN", "1")

        mock_sm_class = MagicMock()
        mock_sm_instance = MagicMock()
        mock_sm_class.return_value = mock_sm_instance

        with patch("main.StateMachine", mock_sm_class):
            from main import main
            main()

        mock_sm_class.assert_called_once()
        mock_sm_instance.run.assert_called_once()

    def test_main_passes_config(self, monkeypatch):
        monkeypatch.setenv("STEMSTOMP_DRY_RUN", "1")
        monkeypatch.setenv("STEMSTOMP_S3_BUCKET", "test-bucket")

        captured_config = {}

        def fake_sm(config):
            captured_config["config"] = config
            mock = MagicMock()
            return mock

        with patch("main.StateMachine", side_effect=fake_sm):
            from main import main
            main()

        assert captured_config["config"].dry_run is True
        assert captured_config["config"].s3_bucket == "test-bucket"
