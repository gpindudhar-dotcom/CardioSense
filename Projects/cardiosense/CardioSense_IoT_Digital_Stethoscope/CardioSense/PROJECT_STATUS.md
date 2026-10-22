# CardioSense Project Status

**Build status: PASS**  
**Frontend build: PASS**  
**Backend tests: PASS**  
**Firmware build: PASS**

Educational prototype — not a medical diagnostic device.

## Validation commands used

```powershell
cd CardioSense

# Python environment + dependencies
python -m venv .venv
.\.venv\Scripts\pip install -r backend\requirements.txt

# Backend / DSP / API / WebSocket tests
.\.venv\Scripts\python -m pytest tests backend\tests -q

# Frontend
cd frontend
npm install
npm run build
cd ..

# Firmware (both PlatformIO environments)
cd firmware\esp32
python -m platformio run
cd ..\..

# Live API smoke check
.\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
# GET http://127.0.0.1:8000/health → status ok
```

## Results summary

| Check | Result |
|-------|--------|
| `pytest` (17 tests) | PASS |
| `npm run build` | PASS |
| PlatformIO `esp32-s3-devkitc-1` | PASS |
| PlatformIO `esp32-s3-generic` | PASS |
| `/health` endpoint | PASS |

## Notes

- Wi-Fi credentials are not committed; configure via firmware `build_flags` / `config.h`.
- Waveform uses real WebSocket sample payloads (not a fake animation).
- BPM and signal quality are derived from signal features; insufficient quality shows `--` / Insufficient signal.
- No medical diagnosis claims in UI or documentation.
