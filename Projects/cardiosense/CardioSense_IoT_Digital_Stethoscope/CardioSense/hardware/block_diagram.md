# System Block Diagram

```text
PATIENT (skin / chest wall contact — educational demo only)
   │
   ▼
STETHOSCOPE CHEST PIECE
   │
   ▼
CONTACT / MEMS MICROPHONE
   │
   ▼
AMPLIFIER / SIGNAL CONDITIONING  (bias, gain, limit to 0–3.3 V)
   │
   ▼
ESP32-S3
   ├─ ADC sampling (default 4000 Hz, configurable)
   ├─ DSP: DC remove → band-pass → envelope → prototype BPM
   ├─ Wi-Fi
   └─ WebSocket binary packets (port 81)
   │
   ▼
BACKEND (FastAPI)
   ├─ /ws/audio bridge
   ├─ SQLite metadata
   └─ WAV recordings
   │
   ▼
WEB DASHBOARD (React + Vite)
   ├─ Live phonocardiogram (real samples)
   ├─ Spectrum / quality / BPM prototype
   └─ Record / play / download

Optional future path:
ESP32-S3 → MQTT → Broker → Backend → Database → Dashboard
```

See also `diagrams/system_architecture.svg`.
