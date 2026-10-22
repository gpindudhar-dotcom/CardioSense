#pragma once

/*
 * Example local secrets / board overrides.
 * Copy to a local override or set build flags in platformio.ini:
 *
 *   build_flags =
 *     -DWIFI_SSID=\"MyNetwork\"
 *     -DWIFI_PASSWORD=\"MyPassword\"
 *     -DADC_PIN=4
 *     -DSAMPLE_RATE=4000
 *     -DBLOCK_SIZE=128
 *
 * Never commit real passwords.
 */

#define WIFI_SSID "YOUR_WIFI_SSID"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"
#define ADC_PIN 4
#define SAMPLE_RATE 4000
#define BLOCK_SIZE 128
#define DEVICE_ID "cardiosense-esp32s3-001"
