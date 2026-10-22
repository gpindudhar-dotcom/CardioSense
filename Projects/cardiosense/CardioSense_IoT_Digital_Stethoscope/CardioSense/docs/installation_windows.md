# Windows 11 Installation (Beginner Friendly)

CardioSense software runs on your PC. ESP32 firmware is flashed separately.

## 1. Install prerequisites

1. **Python 3.11+** — https://www.python.org/downloads/  
   During setup, enable **Add python.exe to PATH**.
2. **Node.js LTS** — https://nodejs.org/  
   Includes `npm`.
3. **Git** (optional) if cloning.
4. **PlatformIO** for firmware:
   ```powershell
   python -m pip install platformio
   ```

Verify:

```powershell
python --version
node --version
npm --version
python -m platformio --version
```

## 2. Unpack the project

Extract `CardioSense_IoT_Digital_Stethoscope.zip` so you have:

```text
CardioSense\
  README.md
  backend\
  frontend\
  firmware\
  ...
```

Open PowerShell:

```powershell
cd path\to\CardioSense
```

## 3. One-command software start

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_windows.ps1
```

This will:

1. Check Python / Node / npm  
2. Create `.venv`  
3. Install backend + frontend dependencies  
4. Start API on `http://127.0.0.1:8000`  
5. Start dashboard on `http://127.0.0.1:5173`

## 4. Flash ESP32 (separate step)

```powershell
cd firmware\esp32
```

Set Wi-Fi via `platformio.ini` `build_flags` or edit `include/config.h`:

```text
WIFI_SSID / WIFI_PASSWORD
ADC_PIN / SAMPLE_RATE / BLOCK_SIZE
```

Then:

```powershell
python -m platformio run --target upload
python -m platformio device monitor -b 115200
```

Note the printed IP. Firmware serves WebSocket audio on **port 81**.

**Verify the exact board pinout before wiring.**

## 5. Manual start (alternative)

Backend:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_backend.ps1
```

Frontend (new terminal):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_frontend.ps1
```

## 6. Open the dashboard

Browser: http://127.0.0.1:5173  
API docs: http://127.0.0.1:8000/docs  

You should see the safety banner:  
**Educational prototype — not a medical diagnostic device.**

## 7. Patient and doctor dashboards

- Patients can register from the dashboard. Patient accounts can see their own recordings and create a one-time doctor sharing code under **Doctor Access**.
- Doctors can create accounts directly from the sign-in page: select **Doctor**, then **Create a doctor account**. Use a password of at least 12 characters.
- A patient gives their 15-minute, single-use code directly to a doctor. The doctor signs in, enters the code under **Shared Patients**, and can view/download that patient's shared recordings. Patients can revoke access under **Doctor Access**.
- The doctor dashboard shows notifications for new recordings shared by linked patients and revoked access. Notifications refresh automatically about every 30 seconds; doctors can also refresh manually and mark items as read.
- Doctor registration is open in this educational prototype and does not verify professional credentials. Do not use it for real patient or clinical information.
- Sessions use HttpOnly cookies; use HTTPS and set `COOKIE_SECURE=1` when hosting beyond localhost. Configure `CORS_ORIGINS` to the exact frontend origins for deployment.
- Existing recordings created before account support have no owner and are not shown in either account dashboard. The prototype is not a clinical records system or medical device.
