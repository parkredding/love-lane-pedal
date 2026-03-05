# StemStomp Developer Guide

## Local Development Setup

```bash
git clone https://github.com/parkredding/love-lane-pedal.git
cd love-lane-pedal
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

## Running in Dry-Run Mode

```bash
STEMSTOMP_DRY_RUN=1 python main.py
```

All hardware modules (GPIO, OLED, audio) operate in stub mode — no physical hardware required.

## Running Tests

```bash
pytest -v                          # Run all tests
pytest --cov=src -v                # With coverage
pytest -k test_config -v           # Run specific test module
pytest -m "not hardware" -v        # Skip hardware tests
```

## Linting and Type Checking

```bash
ruff check src/ tests/             # Lint
ruff format --check src/ tests/    # Format check
mypy src/                          # Type check
```

## Architecture Overview

### Boot Sequence (4 Phases)

1. **HARDWARE_INIT** — Initialize OLED display, show "Booting..."
2. **NETWORK** — Connect to Wi-Fi or launch captive portal
3. **OTA** — Check GitHub Releases for firmware updates (non-fatal)
4. **RUNNING** — Load stems, start cloud sync, register GPIO handlers

### Threading Model

| Thread | Module | Purpose |
|--------|--------|---------|
| Main | state_machine.py | Boot sequence, event loop, display refresh |
| Audio Callback | audio.py | Real-time recording/playback (sounddevice) |
| Cloud Upload | cloud_sync.py | S3 upload queue consumer |
| Cloud Download | cloud_sync.py | S3 polling for new stems |
| GPIO Interrupt | gpio_handler.py | Footswitch event dispatch |
| Display Blink | display.py | 2Hz blink animation |

### Data Flow

```
Microphone → Record Buffer → WAV File → S3 Upload Queue → S3 Bucket
                                                              ↓
                                    Local Stems ← S3 Download Poll
```

### Module Dependency Graph

```
main.py
  └── state_machine.py
        ├── display.py (luma.oled)
        ├── network.py (nmcli, wifi-connect)
        ├── ota.py (requests, GitHub API)
        ├── audio.py (sounddevice, soundfile)
        ├── cloud_sync.py (boto3, S3)
        └── gpio_handler.py (RPi.GPIO)
```

## Configuration

All settings are in `src/config.py`. Load order: defaults → `.env` file → environment variables.

See `.env.template` for all available options.
