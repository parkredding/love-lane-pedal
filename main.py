#!/usr/bin/env python3
"""
StemStomp main entry point.

Reads configuration from environment variables (and optional .env file)
and launches the state machine.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the repo root is on sys.path so ``src`` can be imported even
# when the script is called directly.
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config import StemStompConfig
from src.logging_config import setup_logging
from src.state_machine import StateMachine


def main() -> None:
    config = StemStompConfig.load()
    setup_logging(config.log_level)

    machine = StateMachine(config=config)
    machine.run()


if __name__ == "__main__":
    main()
