# CardioSense ESP32-S3 Firmware

Educational prototype — **not a medical device**.

## Requirements

- PlatformIO Core (`pip install platformio` or VS Code PlatformIO IDE)
- ESP32-S3 development board
- USB data cable

## Configure Wi-Fi and ADC

Edit `include/config.h` **or** set build flags in `platformio.ini`:

```ini
build_flags =
  -DWIFI_SSID=\"YourSSID\"
  -DWIFI_PASSWORD=\"YourPassword\"
  -DADC_PIN=4
  -DSAMPLE_RATE=4000
  -DBLOCK_SIZE=128
```

Do **not** commit real passwords.

**Verify the exact board pinout before wiring.** ADC-capable GPIOs differ across ESP32-S3 modules.

## Build and flash (Windows)

```powershell
cd firmware\esp32
python -m platformio run
python -m platformio run --target upload
python -m platformio device monitor -b 115200
```

## Runtime

After Wi-Fi connects, the board prints its IP. The WebSocket audio server listens on **port 81**.
At the default 4000 Hz sample rate, the 128-sample block sends audio about every 32 ms.

- Binary audio packets: see `docs/architecture.md`
- Text commands: `ping`, `status`

Point the CardioSense backend / dashboard at:

`ws://<ESP32_IP>:81/`

## Safety

- Keep ADC input within 0–3.3 V (biased mid-rail recommended).
- Common ground between amplifier and ESP32.
- Battery and electrical safety: see `hardware/wiring.md`.
