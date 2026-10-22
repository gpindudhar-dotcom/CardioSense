#include <Arduino.h>
#include <WiFi.h>
#include <math.h>

#include "config.h"
#include "wifi_manager.h"
#include "audio_sampler.h"
#include "signal_processing.h"
#include "websocket_server.h"
#include "heart_rate.h"

/*
 * CardioSense ESP32-S3 firmware
 * Educational prototype — not a medical diagnostic device.
 */

static uint32_t g_seq = 0;
static int16_t g_raw[BLOCK_SIZE];
static int16_t g_proc[BLOCK_SIZE];
static uint32_t g_last_status_ms = 0;

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println();
  Serial.println(F("========================================"));
  Serial.println(F(" CardioSense – IoT Digital Stethoscope"));
  Serial.println(F(" EDUCATIONAL PROTOTYPE — NOT A MEDICAL DEVICE"));
  Serial.println(F("========================================"));
  Serial.printf("Device ID   : %s\n", DEVICE_ID);
  Serial.printf("ADC pin     : GPIO%d (verify board pinout!)\n", ADC_PIN);
  Serial.printf("Sample rate : %d Hz\n", SAMPLE_RATE);
  Serial.printf("Block size  : %d\n", BLOCK_SIZE);

  dsp_reset();
  heart_rate_reset();
  heart_rate_configure(40.0f, 180.0f);

  if (!wifi_begin()) {
    Serial.println(F("[WARN] Wi-Fi not connected at boot; will keep retrying."));
  }

  if (!audio_sampler_begin()) {
    Serial.println(F("[ERR] Audio sampler failed to start."));
  }

  if (!ws_server_begin()) {
    Serial.println(F("[ERR] WebSocket server failed to start."));
  }

  Serial.println(F("[OK] Firmware ready."));
}

void loop() {
  wifi_loop();
  audio_sampler_loop();
  ws_server_loop();

  while (audio_sampler_pop_block(g_raw, BLOCK_SIZE)) {
    ProcessedBlock meta{};
    dsp_process_block(g_raw, g_proc, BLOCK_SIZE, (float)SAMPLE_RATE, &meta);

    // Map quality 0..4 to 0..1 score for BPM gating
    float qscore = meta.quality / 4.0f;
    HeartRateResult hr = heart_rate_update(meta.envelope, (float)SAMPLE_RATE, qscore);
    float bpm = (hr.valid && hr.bpm > 0.0f) ? hr.bpm : NAN;

    ws_broadcast_audio_packet(g_proc, BLOCK_SIZE, g_seq++, (float)SAMPLE_RATE, meta, bpm);
  }

  uint32_t now = millis();
  if (now - g_last_status_ms >= 2000) {
    g_last_status_ms = now;
    Serial.printf(
      "[STATUS] wifi=%s ip=%s rssi=%d clients=%d samples=%lu dropped=%lu pkts=%lu\n",
      wifi_is_connected() ? "up" : "down",
      wifi_ip().c_str(),
      wifi_rssi(),
      ws_has_clients() ? 1 : 0,
      (unsigned long)audio_sampler_total_samples(),
      (unsigned long)audio_sampler_dropped_blocks(),
      (unsigned long)ws_packets_sent());
  }
}
