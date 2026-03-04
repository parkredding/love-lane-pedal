#!/usr/bin/env python3
"""
StemStomp main entry point.

Reads optional configuration from environment variables and launches
the state machine.

Environment Variables
---------------------
STEMSTOMP_STEMS_DIR   Path to local stems directory  (default: ./stems)
STEMSTOMP_S3_BUCKET   S3 bucket name for cloud sync  (default: "" = disabled)
STEMSTOMP_DRY_RUN     Set to "1" to run without hardware (testing)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure the repo root is on sys.path so ``src`` can be imported even
# when the script is called directly.
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.state_machine import StateMachine


def main() -> None:
    stems_dir_env = os.environ.get("STEMSTOMP_STEMS_DIR", "")
    stems_dir = Path(stems_dir_env) if stems_dir_env else _ROOT / "stems"

    s3_bucket = os.environ.get("STEMSTOMP_S3_BUCKET", "")
    dry_run = os.environ.get("STEMSTOMP_DRY_RUN", "0") == "1"

    machine = StateMachine(
        stems_dir=stems_dir,
        s3_bucket=s3_bucket,
        dry_run=dry_run,
    )
    machine.run()


if __name__ == "__main__":
    main()
