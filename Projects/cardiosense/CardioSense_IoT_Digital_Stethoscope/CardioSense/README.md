# CardioSense – IoT-Based Digital Stethoscope

**Educational prototype — not a medical diagnostic device.**  
This project does **not** diagnose heart disease, murmurs, arrhythmia, or lung disease. Not for emergency or clinical use. Not clinically validated.

## Project description

CardioSense captures chest sounds with a contact/MEMS microphone, conditions the signal, samples it on an **ESP32-S3**, performs basic DSP, streams audio metrics over Wi-Fi, and visualizes a **live phonocardiogram from real samples** in a React dashboard. It also provides prototype BPM estimation, signal-quality scoring, and local WAV recordings via a FastAPI backend.

## Features

- Configurable ADC pin / sample rate / block size (default **4000 Hz**)
- Wi-Fi with reconnect, WebSocket binary streaming
- DSP: DC removal, band-pass, smoothing, RMS/peak, envelope
- Prototype BPM (40–180 configurable) gated by signal quality
- FastAPI REST + WebSocket + SQLite recordings
- Modern responsive dashboard (dark/light), live canvas waveform, FFT
- Record / play / download / delete WAV
- Windows 11 one-command software start scripts
- Hardware wiring docs + college project report

## Architecture

```text
Chest piece → Mic → Amplifier → ESP32-S3 (ADC/DSP/Wi-Fi)
    → WebSocket → FastAPI backend → React dashboard
Optional: ESP32 → MQTT → broker → backend → DB → dashboard
```

Details: [`docs/architecture.md`](docs/architecture.md)

## Hardware

Primary: ESP32-S3, contact/MEMS mic, amplifier, stethoscope chest piece, power/battery, optional OLED.

**Verify the exact board pinout before wiring.**  
See [`hardware/wiring.md`](hardware/wiring.md), [`hardware/pinout.md`](hardware/pinout.md), [`hardware/bill_of_materials.md`](hardware/bill_of_materials.md).

## Software

| Layer | Stack |
|-------|--------|
| Firmware | PlatformIO, C++, Arduino-ESP32, WebSockets |
| Backend | Python, FastAPI, SQLAlchemy, NumPy, SciPy |
| Frontend | React, Vite, CSS |
| Data | SQLite + WAV files |

## Folder structure

```text
CardioSense/
├── README.md
├── LICENSE
├── .gitignore
├── docker-compose.yml
├── .env.example
├── hardware/
├── firmware/esp32/
├── backend/
├── frontend/
├── data/recordings/
├── scripts/
├── docs/
└── tests/
```

## Installation (Windows 11)

Prerequisites: Python 3.11+, Node.js LTS, npm. PlatformIO for firmware (`python -m pip install platformio`).

```powershell
cd CardioSense
powershell -ExecutionPolicy Bypass -File scripts\start_windows.ps1
```

Full beginner guide: [`docs/installation_windows.md`](docs/installation_windows.md)

### Environment

Copy `.env.example` → `.env` (done automatically by the start script). Important keys:

```text
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
DATABASE_URL=sqlite:///./cardiosense.db
```

Never commit passwords or real Wi-Fi credentials.

## ESP32 flashing

```powershell
cd firmware\esp32
# Configure WIFI_SSID / WIFI_PASSWORD via build_flags or include/config.h
python -m platformio run --target upload
python -m platformio device monitor -b 115200
```

Firmware WebSocket port: **81**. See [`firmware/esp32/README.md`](firmware/esp32/README.md).

> Software start scripts do **not** flash firmware. Flash the ESP32 separately before live hardware streaming.

## Backend setup

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_backend.ps1
```

- API: http://127.0.0.1:8000  
- Docs: http://127.0.0.1:8000/docs  
- Health: http://127.0.0.1:8000/health  

## Frontend setup

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_frontend.ps1
```

Dashboard: http://127.0.0.1:5173

## Running

1. Flash ESP32 and note its IP.  
2. Start backend + frontend (`start_windows.ps1`).  
3. Open the dashboard; click **Connect** if needed.  
4. Stream from device → live waveform uses **actual samples**.  

### Patient and doctor dashboards

The frontend opens to patient/doctor sign-in. Patients can self-register. Doctors can select **Doctor** and then **Create a doctor account** on the same page. Account creation requires a password of at least 12 characters. Doctor registration is open in this educational prototype and does not verify professional credentials.

Patients can create a single-use sharing code in **Doctor Access**. A doctor redeems it from **Shared Patients** to view/download that patient's recordings; patients can revoke access. The doctor dashboard also shows notifications when a patient shares a new recording or revokes access. These account features are for a local educational prototype, not a clinical records system. Existing recordings created before accounts are not assigned to a user.

## Testing

```powershell
powershell -ExecutionPolicy Bypass -File scripts\test_project.ps1
```

Or:

```powershell
.\.venv\Scripts\python -m pytest tests backend\tests -q
cd frontend && npm install && npm run build
cd ..\firmware\esp32 && python -m platformio run
```

## Troubleshooting

See [`docs/troubleshooting.md`](docs/troubleshooting.md).

## Safety

- Educational prototype — not a medical diagnostic device.  
- Not for diagnosis or emergency use.  
- Not clinically validated.  
- Respect ADC voltage range (0–3.3 V), common ground, isolation, and battery BMS practices.  

## Limitations

Classroom-grade fidelity; Wi-Fi jitter; mic coupling sensitivity; single-device local focus; BPM is a prototype estimate that correctly shows `--` when signal quality is poor.

## Future scope

MQTT/cloud storage, mobile app, encryption, multi-device support, ML research classification (non-clinical), clinician-style authenticated dashboards, remote monitoring — documented as **future**, not included as production claims.

## License

MIT — see [`LICENSE`](LICENSE).
