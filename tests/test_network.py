"""Tests for the network management module."""

from unittest.mock import MagicMock, patch

import pytest

from src.network import NetworkManager, NetworkState


class TestNetworkManagerDryRun:
    """Tests that run without any system calls (dry_run=True)."""

    def test_initial_state_is_disconnected(self):
        nm = NetworkManager(dry_run=True)
        assert nm.state == NetworkState.DISCONNECTED

    def test_is_connected_returns_false_when_dry_run(self):
        nm = NetworkManager(dry_run=True)
        assert nm.is_connected() is False

    def test_resolve_enters_ap_mode_when_disconnected(self):
        nm = NetworkManager(dry_run=True)
        # In dry_run mode _check_connected always returns False.
        # _wait_for_connection will time out immediately if timeout=0,
        # so we patch it to return at once.
        with patch.object(nm, "_wait_for_connection"):
            result = nm.resolve()
        assert result == NetworkState.DISCONNECTED


class TestNetworkManagerWithMockedSubprocess:
    def test_resolve_returns_connected_when_nmcli_reports_full(self):
        nm = NetworkManager(dry_run=False)
        mock_result = MagicMock()
        mock_result.stdout = "full\n"

        with patch("subprocess.run", return_value=mock_result):
            state = nm.resolve()

        assert state == NetworkState.CONNECTED

    def test_check_connected_returns_false_on_subprocess_error(self):
        nm = NetworkManager(dry_run=False)
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert nm._check_connected() is False

    def test_start_ap_calls_wifi_connect(self):
        nm = NetworkManager(dry_run=False)
        with patch("subprocess.Popen") as mock_popen:
            nm._start_ap()
            mock_popen.assert_called_once()
            args = mock_popen.call_args[0][0]
            assert "wifi-connect" in args
            assert NetworkManager.AP_SSID in args

    def test_start_ap_ignores_missing_binary(self):
        nm = NetworkManager(dry_run=False)
        with patch("subprocess.Popen", side_effect=FileNotFoundError):
            # Should not raise
            nm._start_ap()
