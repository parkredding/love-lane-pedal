# StemStomp Wiring Reference

## GPIO Pinout (BCM Numbering)

| BCM Pin | Physical Pin | Function | Connection |
|---------|-------------|----------|------------|
| GPIO 17 | Pin 11 | Record Toggle | Footswitch 1 (to GND) |
| GPIO 27 | Pin 13 | Playback Toggle | Footswitch 2 (to GND) |
| GPIO 22 | Pin 15 | Sync Trigger | Footswitch 3 (to GND) |
| SDA1 | Pin 3 | I2C Data | SSD1306 SDA |
| SCL1 | Pin 5 | I2C Clock | SSD1306 SCL |
| 3.3V | Pin 1 | Power | SSD1306 VCC |
| GND | Pin 6 | Ground | SSD1306 GND, Footswitches |

## Footswitch Wiring

Each footswitch connects between the GPIO pin and GND. Internal pull-up resistors are enabled in software (GPIO.PUD_UP), so no external resistors are needed.

```
GPIO Pin ──── Footswitch ──── GND
```

Debounce: 200ms (configured in software)
Trigger: Falling edge (press = LOW)

## OLED Display (SSD1306)

- Interface: I2C
- Port: 1 (default)
- Address: 0x3C (default)
- Resolution: 128x64 pixels

```
Pi 3.3V ──── VCC
Pi GND  ──── GND
Pi SDA1 ──── SDA
Pi SCL1 ──── SCL
```

## Audio Interface

Connect any USB class-compliant audio interface. The system uses:
- Sample rate: 44.1 kHz
- Channels: Mono (1)
- Bit depth: 24-bit (PCM_24 in 32-bit container)
- Block size: 1024 frames (~23ms latency)
