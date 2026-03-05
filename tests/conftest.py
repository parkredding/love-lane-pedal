"""Shared test fixtures for StemStomp."""

import pytest
from pathlib import Path

from src.config import StemStompConfig


@pytest.fixture
def tmp_stems_dir(tmp_path):
    """Return a temporary stems directory."""
    d = tmp_path / "stems"
    d.mkdir()
    return d


@pytest.fixture
def dry_run_config(tmp_stems_dir):
    """Return a StemStompConfig with dry_run=True."""
    return StemStompConfig(
        stems_dir=tmp_stems_dir,
        dry_run=True,
    )
