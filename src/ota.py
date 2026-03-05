"""
OTA (Over-The-Air) firmware update pipeline for StemStomp.

Queries the GitHub Releases API, compares the remote tag against the
local version.txt, and – if a newer version exists – downloads and
installs the binary asset.
"""

from __future__ import annotations

import os
import stat
import shutil
import tempfile
from pathlib import Path
from typing import Optional

import requests

VERSION_FILE = Path(__file__).resolve().parent.parent / "version.txt"
GITHUB_REPO = "parkredding/love-lane-pedal"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
ASSET_NAME = "stemstomp"  # name of the compiled binary asset in the release


def read_local_version() -> str:
    """Return the version string stored in version.txt (stripped)."""
    try:
        return VERSION_FILE.read_text().strip()
    except FileNotFoundError:
        return "v0.0.0"


def fetch_latest_release(timeout: int = 10) -> dict:
    """
    Query the GitHub Releases API and return the parsed JSON.

    Raises ``requests.RequestException`` on network errors.
    """
    resp = requests.get(
        GITHUB_API_URL,
        headers={"Accept": "application/vnd.github+json"},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()


def _parse_version(version: str) -> tuple:
    """Parse a version string like 'v0.1.0' into a comparable tuple."""
    parts = version.lstrip("v").split(".")
    result = []
    for part in parts:
        try:
            result.append(int(part))
        except ValueError:
            result.append(0)
    return tuple(result)


def update_available(local_version: str, remote_tag: str) -> bool:
    """
    Return True when *remote_tag* is strictly newer than *local_version*.

    Uses semantic version ordering so that a remote version older than
    or equal to the local version will not trigger an update.
    """
    return _parse_version(remote_tag) > _parse_version(local_version)


def download_asset(release: dict, dest_path: Path, timeout: int = 60) -> bool:
    """
    Find the binary asset in *release* and download it to *dest_path*.

    Returns True on success, False if the asset was not found.
    """
    asset_url: Optional[str] = None
    for asset in release.get("assets", []):
        if asset.get("name") == ASSET_NAME:
            asset_url = asset["browser_download_url"]
            break

    if asset_url is None:
        return False

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        resp = requests.get(asset_url, stream=True, timeout=timeout)
        resp.raise_for_status()
        with open(tmp_path, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=8192):
                fh.write(chunk)

        # Atomic replace
        shutil.move(str(tmp_path), str(dest_path))

        # Make the binary executable
        current_mode = dest_path.stat().st_mode
        dest_path.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        return True
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise


def run_ota(install_dir: Optional[Path] = None) -> bool:
    """
    Full OTA pipeline entry-point.

    1. Read local version.
    2. Fetch remote release.
    3. If update available, download and install.

    Returns True if an update was installed, False otherwise.
    Raises on network or I/O errors so the caller can show an error
    state on the OLED.
    """
    local = read_local_version()
    release = fetch_latest_release()
    remote_tag = release.get("tag_name", "")

    if not update_available(local, remote_tag):
        return False

    if install_dir is None:
        install_dir = Path(__file__).resolve().parent.parent / "bin"
    install_dir.mkdir(parents=True, exist_ok=True)

    dest = install_dir / ASSET_NAME
    success = download_asset(release, dest)

    if success:
        VERSION_FILE.write_text(remote_tag + "\n")

    return success
