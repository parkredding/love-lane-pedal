"""
Centralized configuration for StemStomp.

Loads settings from defaults, then .env file, then environment variables.
Environment variables always take precedence.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_env_file(path: Path) -> dict[str, str]:
    """Parse a simple .env file (KEY=VALUE, ignoring comments and blanks)."""
    env = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip()
    return env


@dataclass(frozen=True)
class StemStompConfig:
    """Immutable configuration for a StemStomp instance."""

    stems_dir: Path = field(default_factory=lambda: Path("./stems"))
    s3_bucket: str = ""
    s3_prefix: str = "stems/"
    dry_run: bool = False
    log_level: str = "INFO"
    sync_poll_interval: int = 30

    # GPIO pin assignments (BCM numbering)
    gpio_pin_record: int = 17
    gpio_pin_playback: int = 27
    gpio_pin_sync: int = 22

    # OLED display
    oled_i2c_port: int = 1
    oled_i2c_address: int = 0x3C

    # OTA
    github_repo: str = "parkredding/love-lane-pedal"
    ota_asset_name: str = "stemstomp"

    @classmethod
    def load(cls, env_file: Path | None = None) -> StemStompConfig:
        """
        Build config from defaults -> .env file -> environment variables.

        Environment variables override .env file values, which override defaults.
        """
        file_env: dict[str, str] = {}
        if env_file is None:
            # Look for .env next to the project root
            candidate = Path(__file__).resolve().parent.parent / ".env"
            if candidate.exists():
                file_env = _load_env_file(candidate)
        elif env_file.exists():
            file_env = _load_env_file(env_file)

        def get(key: str, default: str = "") -> str:
            return os.environ.get(key, file_env.get(key, default))

        stems_dir_str = get("STEMSTOMP_STEMS_DIR", "")
        root = Path(__file__).resolve().parent.parent
        stems_dir = Path(stems_dir_str) if stems_dir_str else root / "stems"

        oled_addr_str = get("STEMSTOMP_OLED_ADDRESS", "0x3C")
        try:
            oled_address = int(oled_addr_str, 0)
        except ValueError:
            oled_address = 0x3C

        return cls(
            stems_dir=stems_dir,
            s3_bucket=get("STEMSTOMP_S3_BUCKET", ""),
            s3_prefix=get("STEMSTOMP_S3_PREFIX", "stems/"),
            dry_run=get("STEMSTOMP_DRY_RUN", "0") == "1",
            log_level=get("STEMSTOMP_LOG_LEVEL", "INFO"),
            sync_poll_interval=int(get("STEMSTOMP_SYNC_INTERVAL", "30")),
            gpio_pin_record=int(get("STEMSTOMP_GPIO_RECORD", "17")),
            gpio_pin_playback=int(get("STEMSTOMP_GPIO_PLAYBACK", "27")),
            gpio_pin_sync=int(get("STEMSTOMP_GPIO_SYNC", "22")),
            oled_i2c_port=int(get("STEMSTOMP_OLED_PORT", "1")),
            oled_i2c_address=oled_address,
            github_repo=get("STEMSTOMP_GITHUB_REPO", "parkredding/love-lane-pedal"),
            ota_asset_name=get("STEMSTOMP_OTA_ASSET", "stemstomp"),
        )
