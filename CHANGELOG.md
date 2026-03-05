# Changelog

## [0.1.0] - 2026-03-04

### Added
- 4-phase boot state machine (hardware init, network, OTA, running)
- 24-bit/44.1kHz mono audio recording and multi-track playback
- S3 cloud sync with background upload and download threads
- SSD1306 OLED display with 9 UI states and blink animations
- Wi-Fi provisioning via captive portal (balena wifi-connect)
- GPIO footswitch handling with 200ms debounce (record, playback, sync)
- OTA firmware updates via GitHub Releases API
- Full pytest suite with hardware mocking for all modules
- Systemd service files for auto-start on Raspberry Pi
- Centralized configuration via environment variables and .env file
- Structured logging via Python logging module
- Health check module for system monitoring
- CI/CD pipeline (GitHub Actions) with linting, type checking, and tests
- Deployment automation scripts (provision.sh, deploy.sh)
- Security-hardened systemd service configuration
