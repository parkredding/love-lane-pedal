# StemStomp

A standalone, Wi-Fi-enabled digital effects pedal for recording, uploading, and syncing multi-track audio stems directly from a pedalboard to the cloud.

## Features

- **24-bit/44.1kHz audio recording** with real-time monitoring
- **Multi-track playback** with automatic stem mixing
- **Cloud sync** via AWS S3 (background upload/download)
- **OLED display** (SSD1306 128x64) showing system status
- **Wi-Fi provisioning** via captive portal
- **OTA updates** from GitHub Releases
- **3 footswitches** — Record, Playback, Sync

## Quick Start

```bash
# On a Raspberry Pi with the hardware connected:
git clone https://github.com/parkredding/love-lane-pedal.git
cd love-lane-pedal
sudo bash scripts/provision.sh
# Edit /opt/stemstomp/.env to set your S3 bucket
sudo systemctl start stemstomp
```

## Development

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
STEMSTOMP_DRY_RUN=1 python main.py   # Run without hardware
pytest -v                              # Run tests
```

## Documentation

- [Setup Guide](docs/setup-guide.md) — Hardware requirements, provisioning, configuration
- [Developer Guide](docs/developer-guide.md) — Local development, architecture, testing
- [Wiring Reference](docs/wiring.md) — GPIO pinout, OLED, footswitch connections
- [AWS Setup](docs/aws-setup.md) — S3 bucket, IAM policy, credentials

## License

Copyright © 2026 Derek DeBoer and Parker Redding. All rights reserved.

This software and associated documentation files (the "Software") are the proprietary and confidential property of Derek DeBoer and Parker Redding. No part of the Software may be reproduced, distributed, transmitted, displayed, published, or broadcast in any form or by any means, or used to make derivative works, without the prior written permission of the copyright owners.

Unauthorized copying, modification, or distribution of this Software, in whole or in part, is strictly prohibited.