# Testing

## Automated (Windows)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\test_project.ps1
```

Or manually:

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r backend\requirements.txt
.\.venv\Scripts\python -m pytest tests backend\tests -q

cd frontend
npm install
npm run build
cd ..

cd firmware\esp32
python -m platformio run
```

## What is covered

| Area | Tests |
|------|--------|
| Filters / RMS / peaks | `tests/test_signal_processing.py` |
| BPM estimator | `tests/test_heart_rate.py` |
| Signal quality | `tests/test_signal_processing.py` |
| WAV generation | `tests/test_signal_processing.py` |
| API + WebSocket packets | `backend/tests/test_api.py` |
| Frontend production build | `npm run build` |
| Firmware compile | PlatformIO `run` |

## Manual UI checks

1. Backend health returns OK.  
2. Dashboard connects to `/ws/audio`.  
3. With ESP32 streaming (or a packet injector), waveform shows **real samples**.  
4. Start/Stop recording creates WAV download.  
5. Low-noise input shows `--` BPM and Insufficient signal.
