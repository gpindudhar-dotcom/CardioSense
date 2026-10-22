# ESP32-S3 Pinout Notes

**Verify the exact board pinout before wiring.**

CardioSense defaults:

| Function | Config constant | Default | Remarks |
|----------|-----------------|---------|---------|
| Analog audio in | `ADC_PIN` | GPIO **4** | Must be ADC1-capable on your board |
| Serial debug | USB CDC | USB | `115200` baud |
| WebSocket server | `HTTP_PORT` | **81** | SoftAP/STA IP printed on Serial |
| Optional OLED SDA | board-specific | often GPIO8 | Optional |
| Optional OLED SCL | board-specific | often GPIO9 | Optional |

## Changing the ADC pin

1. Confirm the GPIO is ADC-capable on **your** ESP32-S3 module datasheet.
2. Update `firmware/esp32/include/config.h` or PlatformIO `build_flags`:
   `-DADC_PIN=5`
3. Rewire amplifier OUT to that GPIO.
4. Rebuild and flash.

## Boards differ

Examples of naming differences across vendors:

- “IO4” vs “A3” vs “GPIO4”
- Some pins used by PSRAM / flash / USB — avoid those for ADC
- Strapping pins can affect boot if pulled incorrectly

If unsure, use the vendor pinout PDF for your exact DevKit revision.
