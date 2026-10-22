# CardioSense – IoT-Based Digital Stethoscope
## College Engineering Project Report

**Classification:** Educational prototype — **not a medical device**  
**Do not use for diagnosis, emergency care, or clinical decisions.**

---

### 1. Abstract

CardioSense is an educational Internet of Things (IoT) system that captures chest/heart sounds with a contact or MEMS microphone, conditions the analog signal, samples it on an ESP32-S3 microcontroller, applies basic digital signal processing (DSP), and streams data over Wi-Fi to a Python FastAPI backend and a React web dashboard. The dashboard displays a live phonocardiogram from **real received samples**, estimates a **prototype** heart-rate (BPM) value, reports signal quality, and stores WAV recordings locally. The work demonstrates embedded sampling, DSP, networking, and full-stack visualization for academic learning. It is **not clinically validated** and must not be represented as a diagnostic instrument.

### 2. Introduction

Traditional acoustic stethoscopes remain essential teaching tools, but modern curricula also emphasize embedded systems, wireless connectivity, and interactive visualization. CardioSense integrates these topics into one runnable prototype: hardware front-end, firmware, backend services, and a responsive UI.

### 3. Problem Statement

Students need a safe, documented, end-to-end platform to study:

- analog microphone conditioning and ADC limits,
- real-time sampling and buffering,
- basic biomedical-adjacent DSP (without clinical claims),
- IoT transport (WebSocket / optional MQTT),
- web dashboards for live signals and recordings.

Commercial medical devices are unsuitable for unrestricted student modification and carry regulatory constraints. An explicitly non-clinical educational kit addresses the gap.

### 4. Objectives

1. Capture and amplify microphone signals for ESP32-S3 ADC input.  
2. Sample at a configurable rate (default 4000 Hz).  
3. Implement DC removal, filtering, RMS/peak, envelope, and prototype BPM estimation.  
4. Stream binary packets over Wi-Fi.  
5. Provide FastAPI REST + WebSocket services with SQLite metadata.  
6. Render a modern dashboard with live waveform, spectrum, quality, and recording tools.  
7. Document wiring, safety, Windows 11 setup, and limitations clearly.

### 5. Existing System

Acoustic teaching stethoscopes provide no digital capture. Research and hobby “electronic stethoscope” projects exist but often lack complete, tested firmware+backend+frontend packaging, Windows onboarding, or explicit non-medical labeling. CardioSense focuses on a complete reproducible repository rather than clinical performance.

### 6. Proposed System

A modular stack: chest piece → mic → amplifier → ESP32-S3 → Wi-Fi WebSocket → FastAPI → React dashboard, with local WAV storage and optional MQTT architecture documented for future work.

### 7. System Architecture

See `docs/architecture.md` and `hardware/diagrams/system_architecture.svg`. Layers include sensing, embedded DSP, network transport, application API, persistence, and presentation.

### 8. Hardware Requirements

ESP32-S3 DevKit, contact/MEMS microphone, amplifier/conditioning, stethoscope chest piece, power supply/battery with protection, optional OLED. Full list: `hardware/bill_of_materials.md`.

### 9. Software Requirements

- Firmware: C++ / Arduino framework / PlatformIO  
- Backend: Python 3, FastAPI, SQLAlchemy, NumPy, SciPy  
- Frontend: React 18, Vite, modern CSS  
- OS target for lab PCs: Windows 11  

### 10. Circuit Description

Amplifier output is biased into the ESP32 ADC range (0–3.3 V) with common ground. Default ADC example pin is GPIO4 (`ADC_PIN`), which **must be verified** against the specific board pinout. Details: `hardware/wiring.md`, `hardware/pinout.md`.

### 11. IoT Architecture

Primary path uses WebSocket binary frames. Backend bridges device packets to browser clients as JSON audio messages containing the actual sample arrays. Optional MQTT broker profile is provided in `docker-compose.yml` for experimentation.

### 12. ESP32 Firmware

Modules: `wifi_manager`, `audio_sampler`, `signal_processing`, `heart_rate`, `websocket_server`. Configuration constants (`WIFI_SSID`, `ADC_PIN`, `SAMPLE_RATE`, `BLOCK_SIZE`) are easy to change without hardcoding production secrets in shared source.

### 13. Signal Processing

Pipeline: DC removal → band-pass (≈20–400 Hz experimental band) → smoothing → amplitude metrics → envelope → event detection. Described in `docs/signal_processing.md`.

### 14. BPM Algorithm

Prototype estimator detects repeated envelope peaks, rejects unrealistic intervals outside configurable min/max BPM (default 40–180), averages multiple intervals, and gates on signal quality. Output is labeled: **Prototype estimate – not clinically validated.** Insufficient quality yields `--` BPM / Insufficient signal.

### 15. Backend

FastAPI application exposes health, device status, recordings CRUD, analysis helpers, and `/ws/audio`. SQLite stores recording metadata without unnecessary personal data.

### 16. Frontend

CardioSense dashboard with sidebar navigation (Live Monitor, Recordings, Signal Analysis, Settings), metric cards, live canvas phonocardiogram driven by a sample ring buffer, FFT panel, device status, recording controls, dark/light theme, and a persistent safety notice.

### 17. Database

Table `recordings`: id, timestamp, duration, sample rate, sample count, device id, estimated BPM, signal quality, filename, optional notes. Audio payloads stored as WAV files under `data/recordings/`.

### 18. Testing

Unit tests cover filters, RMS, peaks, BPM, quality, WAV headers, and API/WebSocket parsing. Frontend production build and PlatformIO firmware compile are part of validation (`scripts/test_project.ps1`).

### 19. Results

On synthetic pulse trains, the BPM estimator converges near the programmed rate within tolerance in unit tests. The dashboard displays live samples when packets arrive; recordings export valid RIFF/WAV files. Qualitative hardware results depend on microphone coupling and noise environment and are educational only.

### 20. Limitations

- Not medically validated; unsuitable for diagnosis or monitoring of patients.  
- ADC timing jitter and Wi-Fi latency affect fidelity.  
- Contact mic quality and motion artifacts dominate signal quality.  
- Single-device local demo focus.  
- BPM may read `--` with weak coupling (expected safe behavior).

### 21. Future Scope

MQTT cloud relay, encrypted transport, multi-device registry, authenticated clinician-style dashboards, mobile apps, cloud object storage, and ML-based **research** classifiers clearly labeled non-clinical. See README Future Scope.

### 22. Safety

Visible UI and documentation notice: educational prototype — not a medical diagnostic device. Observe electrical isolation practices, ADC voltage limits, battery BMS usage, and never claim disease diagnosis capability.

### 23. Conclusion

CardioSense delivers a complete, runnable educational IoT digital stethoscope stack—from ESP32-S3 sampling to a modern web dashboard—emphasizing engineering learning, reproducible setup on Windows 11, and explicit non-medical boundaries.

### 24. References

1. Espressif Systems. ESP32-S3 Technical Reference Manual.  
2. FastAPI documentation. https://fastapi.tiangolo.com/  
3. React documentation. https://react.dev/  
4. PlatformIO documentation. https://docs.platformio.org/  
5. Oppenheim, A. V., & Schafer, R. W. Discrete-Time Signal Processing.  
6. IEEE / academic surveys on electronic auscultation (background reading only; not clinical endorsement).
