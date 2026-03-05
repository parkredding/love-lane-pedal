# StemStomp Setup Guide

## Hardware Requirements

- Raspberry Pi 4 Model B (2GB+ RAM recommended)
- USB audio interface (class-compliant, 24-bit capable)
- SSD1306 OLED display (128x64, I2C)
- 3x momentary footswitches (normally open)
- microSD card (16GB+)
- 5V 3A USB-C power supply
- Enclosure (Hammond 1590BB or similar)

## Wiring

See [wiring.md](wiring.md) for detailed GPIO pinout and connections.

## Software Setup

### 1. Flash Raspberry Pi OS

Flash Raspberry Pi OS Lite (Bookworm, 64-bit) to your microSD card using the Raspberry Pi Imager. Enable SSH during setup.

### 2. Clone the Repository

```bash
git clone https://github.com/parkredding/love-lane-pedal.git
cd love-lane-pedal
```

### 3. Run the Provisioning Script

```bash
sudo bash scripts/provision.sh
```

This will:
- Create the `stemstomp` system user
- Install system dependencies (ALSA, PortAudio, I2C tools)
- Set up a Python virtual environment at `/opt/stemstomp`
- Install systemd services
- Enable I2C and SPI interfaces

### 4. Configure

Edit `/opt/stemstomp/.env`:

```bash
sudo nano /opt/stemstomp/.env
```

At minimum, set your S3 bucket name:
```
STEMSTOMP_S3_BUCKET=your-bucket-name
```

See [aws-setup.md](aws-setup.md) for IAM credential setup.

### 5. Start

```bash
sudo systemctl start stemstomp
```

Check logs:
```bash
journalctl -u stemstomp -f
```

## Updating

```bash
cd love-lane-pedal
git pull
sudo bash scripts/deploy.sh
```
