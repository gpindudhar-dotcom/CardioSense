# Hardware Wiring Guide

**Educational prototype — not a medical device.**  
**Verify the exact board pinout before wiring.** ESP32-S3 development boards do **not** share identical silk-screen labels.

## Overview

```
Chest piece → Contact/MEMS mic → Amplifier / conditioning → ESP32-S3 ADC → DSP / Wi-Fi
```

## Recommended connections (example)

| Signal | From | To (example ESP32-S3) | Notes |
|--------|------|------------------------|-------|
| Mic audio out | Amplifier OUT | GPIO4 (ADC1) | Change `ADC_PIN` in firmware if needed |
| Mic / amp GND | Amplifier GND | ESP32 GND | **Common ground required** |
| Mic / amp VCC | 3.3 V regulated | 3.3 V | Do not feed 5 V into ESP32 ADC path |
| ESP32 USB | USB | PC | Programming / debug |
| Battery + | Li-ion protection / 5 V boost | 5 V VIN or USB | Use proper BMS; observe polarity |
| Battery − | Battery pack − | GND | |

Optional OLED (I2C): SDA/SCL on board-specific pins (often GPIO8/9). OLED is optional and not required for the web dashboard.

## ADC voltage limits

- ESP32-S3 ADC inputs are **0 V to ~3.3 V** (attenuation dependent).
- Amplifier output **must** stay within this range.
- Prefer mid-rail bias (~1.65 V) so AC heart sounds swing above/below the bias without clipping at 0 V.
- Never connect an unconditioned electret mic directly to ADC without biasing and limiting.

## Signal biasing

1. Amplifier DC-coupled output should be centered near mid-supply.
2. If using AC coupling, add a bias tee (resistors to 1.65 V) before ADC.
3. Firmware estimates DC mid-point at boot and subtracts it.

## Common ground

All modules (mic amp, ESP32, power supply) must share a common GND reference. Floating grounds cause noise and can damage ADC inputs.

## Microphone supply

- MEMS / electret capsules typically need clean 1.8–3.3 V.
- Keep digital Wi-Fi antenna currents away from analog traces.
- Short analog wires; twisted pair for mic leads when possible.

## Battery precautions

- Use protected cells / BMS.
- Do not charge unattended DIY packs.
- Avoid reverse polarity.
- If using USB and battery simultaneously, ensure the power path is designed for it (or power from one source only).

## Electrical / sensor safety

- This is a classroom / hobby prototype.
- Do not connect electrodes that could inject current into a person.
- Keep the chest piece mechanically coupled; do not create conductive patient pathways to mains or USB earth in unsafe ways.
- Use isolation practices appropriate for student labs.

## Noise tips

- Add a simple RC low-pass before ADC (~1–2 kHz cutoff) if RF noise is severe.
- Keep sample rate at 4000 Hz unless you change firmware + backend settings together.
