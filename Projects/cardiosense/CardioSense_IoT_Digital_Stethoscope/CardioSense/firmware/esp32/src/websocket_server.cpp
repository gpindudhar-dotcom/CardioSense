#include "websocket_server.h"
#include "wifi_manager.h"
#include "config.h"

#include <WebSocketsServer.h>
#include <WiFi.h>
#include <ArduinoJson.h>
#include <string.h>

/*
 * Binary packet format (little-endian):
 * Offset  Size  Field
 * 0       4     magic = 0x44534E43 ('CSND')
 * 4       1     version = 1
 * 5       1     flags (bit0=processed)
 * 6       2     sample_count (N)
 * 8       4     sequence
 * 12      4     sample_rate (float)
 * 16      4     rms (float)
 * 20      4     peak (float)
 * 24      4     bpm (float, NaN if invalid)
 * 28      1     quality (0-4)
 * 29      3     reserved
 * 32      2*N   int16 PCM samples
 *
 * Also serves JSON status on text frames and HTTP GET /status on port HTTP_PORT via WS library events.
 */

static WebSocketsServer s_ws(HTTP_PORT);
static uint32_t s_packets_sent = 0;
static bool s_started = false;

static void send_status_to(uint8_t num) {
  JsonDocument doc;
  doc["type"] = "status";
  doc["device_id"] = DEVICE_ID;
  doc["wifi_connected"] = wifi_is_connected();
  doc["ip"] = wifi_ip();
  doc["rssi"] = wifi_rssi();
  doc["sample_rate"] = SAMPLE_RATE;
  doc["block_size"] = BLOCK_SIZE;
  doc["adc_pin"] = ADC_PIN;
  doc["packets_sent"] = s_packets_sent;
  doc["educational_notice"] = "Educational prototype — not a medical diagnostic device.";
  String out;
  serializeJson(doc, out);
  s_ws.sendTXT(num, out);
}

static void on_ws_event(uint8_t num, WStype_t type, uint8_t *payload, size_t length) {
  switch (type) {
    case WStype_CONNECTED:
      Serial.printf("[WS] Client %u connected\n", num);
      send_status_to(num);
      break;
    case WStype_DISCONNECTED:
      Serial.printf("[WS] Client %u disconnected\n", num);
      break;
    case WStype_TEXT:
      if (payload && length > 0) {
        if (strncmp((const char *)payload, "ping", 4) == 0) {
          s_ws.sendTXT(num, "{\"type\":\"pong\"}");
        } else if (strncmp((const char *)payload, "status", 6) == 0) {
          send_status_to(num);
        }
      }
      break;
    default:
      break;
  }
}

bool ws_server_begin() {
  s_ws.begin();
  s_ws.onEvent(on_ws_event);
  s_started = true;
  Serial.printf("[WS] Server on port %d path /\n", HTTP_PORT);
  return true;
}

void ws_server_loop() {
  if (s_started) {
    s_ws.loop();
  }
}

void ws_broadcast_audio_packet(const int16_t *samples, size_t count, uint32_t seq,
                               float sample_rate, const ProcessedBlock &meta, float bpm) {
  if (!s_started || count == 0 || count > 2048) {
    return;
  }

  const size_t header = 32;
  const size_t bytes = header + count * sizeof(int16_t);
  static uint8_t buf[32 + 2048 * 2];
  if (bytes > sizeof(buf)) {
    return;
  }

  memset(buf, 0, header);
  uint32_t magic = PACKET_MAGIC;
  memcpy(buf + 0, &magic, 4);
  buf[4] = PACKET_VERSION;
  buf[5] = 0x01; // processed
  uint16_t n = (uint16_t)count;
  memcpy(buf + 6, &n, 2);
  memcpy(buf + 8, &seq, 4);
  memcpy(buf + 12, &sample_rate, 4);
  float rms = meta.rms;
  float peak = meta.peak;
  memcpy(buf + 16, &rms, 4);
  memcpy(buf + 20, &peak, 4);
  memcpy(buf + 24, &bpm, 4);
  buf[28] = meta.quality;
  memcpy(buf + 32, samples, count * sizeof(int16_t));

  s_ws.broadcastBIN(buf, bytes);
  s_packets_sent++;
}

bool ws_has_clients() {
  // WebSocketsServer does not expose count portably; approximate via packets / connections logs.
  return s_started;
}

uint32_t ws_packets_sent() {
  return s_packets_sent;
}
