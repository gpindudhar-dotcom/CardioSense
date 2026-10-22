#pragma once

/*
 * CardioSense ESP32-S3 configuration
 * ----------------------------------
 * Copy values from config.example.h / set locally.
 * Do NOT commit real Wi-Fi credentials.
 * Verify ADC pin against your exact ESP32-S3 board pinout before wiring.
 */

#ifndef WIFI_SSID
#define WIFI_SSID "YOUR_WIFI_SSID"
#endif

#ifndef WIFI_PASSWORD
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"
#endif

// Default ADC GPIO for many ESP32-S3 DevKit boards (ADC1_CHANNEL_3 / GPIO4).
// CHANGE THIS to match your board — verify the exact board pinout before wiring.
#ifndef ADC_PIN
#define ADC_PIN 4
#endif

#ifndef SAMPLE_RATE
#define SAMPLE_RATE 4000
#endif

#ifndef BLOCK_SIZE
#define BLOCK_SIZE 128
#endif

#ifndef DEVICE_ID
#define DEVICE_ID "cardiosense-esp32s3-001"
#endif

#ifndef WS_PATH
#define WS_PATH "/ws"
#endif

#ifndef HTTP_PORT
#define HTTP_PORT 81
#endif

// Heart-sound experimental band (Hz) — educational DSP defaults
#ifndef HPF_CUTOFF_HZ
#define HPF_CUTOFF_HZ 20.0f
#endif

#ifndef LPF_CUTOFF_HZ
#define LPF_CUTOFF_HZ 400.0f
#endif

#ifndef RING_BUFFER_BLOCKS
#define RING_BUFFER_BLOCKS 8
#endif

// Packet magic: 'C''S''N''D' = CardioSense Audio
#define PACKET_MAGIC 0x44534E43u
#define PACKET_VERSION 1
