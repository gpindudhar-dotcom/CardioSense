# Architecture

**CardioSense** is an educational IoT digital stethoscope prototype. It is **not** a medical device and cannot diagnose disease.

## Data path

1. Acoustic energy at chest piece → microphone → analog conditioning  
2. ESP32-S3 ADC samples at configurable rate (default **4000 Hz**)  
3. On-device DSP: DC removal, smoothing, band-pass (~20–400 Hz), RMS/peak, envelope  
4. Prototype BPM estimate (firmware + backend refinement)  
5. Binary WebSocket packets from ESP32 (server on port **81**)  
6. Backend **device bridge** (`POST /api/device/connect`) pulls packets and fans them out on `/ws/audio`  
7. React dashboard renders **real samples** on a canvas phonocardiogram  

The default 128-sample audio block at 4000 Hz gives approximately 32 ms of packetization latency. Reflash the ESP32 after changing firmware settings.

Optional future: MQTT broker path (disabled by default).

## Binary packet format

Little-endian layout used by firmware and backend:

| Offset | Size | Field |
|--------|------|-------|
| 0 | 4 | `magic` = `0x44534E43` (`CSND`) |
| 4 | 1 | `version` = 1 |
| 5 | 1 | `flags` (bit0 = processed) |
| 6 | 2 | `sample_count` N |
| 8 | 4 | `sequence` uint32 |
| 12 | 4 | `sample_rate` float32 |
| 16 | 4 | `rms` float32 |
| 20 | 4 | `peak` float32 |
| 24 | 4 | `bpm` float32 (`NaN` if invalid) |
| 28 | 1 | `quality` 0–4 |
| 29 | 3 | reserved |
| 32 | 2×N | `int16` PCM samples |

## Backend API

- `GET /health`
- `GET /api/device/status`
- `WS /ws/audio`
- `POST/GET/DELETE /api/recordings` (+ download)

Interactive docs: `http://127.0.0.1:8000/docs`

## Configuration

| Item | Where |
|------|--------|
| Wi-Fi SSID/password | Firmware build flags / `config.h` (never commit secrets) |
| `ADC_PIN`, `SAMPLE_RATE`, `BLOCK_SIZE` | `firmware/esp32/include/config.h` |
| Backend host/DB | `.env` / `backend/.env` |

## Safety

Educational prototype — not a medical diagnostic device. Observe ADC voltage range, isolation, and battery safety (`hardware/wiring.md`).
