# Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Backend unavailable | Port 8000 busy / venv missing | Run `scripts/start_backend.ps1`; free port 8000 |
| Frontend blank | `npm install` failed | Delete `frontend/node_modules` and reinstall |
| WebSocket disconnects | Backend down | Restart uvicorn; check firewall |
| ESP32 Wi-Fi fail | Bad SSID/password | Set build flags; avoid committed secrets |
| No waveform | No packets | Confirm ESP32 IP, port 81, backend bridge; Serial logs |
| BPM always `--` | Low quality / noise | Improve contact, gain, bias; wait for warm-up |
| ADC clipping / Poor quality | Gain too high | Lower amp gain; verify 0–3.3 V range |
| Wrong ADC pin | Board pinout mismatch | **Verify exact board pinout**; change `ADC_PIN` |
| PlatformIO not found | Not installed / PATH | `python -m pip install platformio` then `python -m platformio` |
| `scipy` install fails | Python too new | Use Python 3.11–3.12 for best wheel support |
| WAV play fails | Browser autoplay / missing file | Use Play button after Stop Recording; check `data/recordings` |
| Database errors | Locked SQLite / bad path | Delete `cardiosense.db` for local reset (loses metadata) |

## Safety reminders

- Educational prototype — not a medical diagnostic device.  
- Do not use for emergency decisions.  
- Keep inputs within ADC limits; common ground; battery BMS.
