#include "wifi_manager.h"
#include "config.h"
#include <WiFi.h>

static uint32_t s_last_attempt_ms = 0;
static uint32_t s_reconnect_count = 0;
static bool s_was_connected = false;

bool wifi_begin() {
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.persistent(false);

  if (String(WIFI_SSID) == "YOUR_WIFI_SSID") {
    Serial.println(F("[WiFi] SSID not configured. Set WIFI_SSID / WIFI_PASSWORD in build_flags or config.h"));
    return false;
  }

  Serial.printf("[WiFi] Connecting to '%s'...\n", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  s_last_attempt_ms = millis();

  const uint32_t timeout_ms = 15000;
  while (WiFi.status() != WL_CONNECTED && (millis() - s_last_attempt_ms) < timeout_ms) {
    delay(250);
    Serial.print('.');
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    s_was_connected = true;
    Serial.printf("[WiFi] Connected. IP=%s RSSI=%d\n", WiFi.localIP().toString().c_str(), WiFi.RSSI());
    return true;
  }

  Serial.println(F("[WiFi] Initial connection failed; will retry in loop."));
  return false;
}

void wifi_loop() {
  if (WiFi.status() == WL_CONNECTED) {
    if (!s_was_connected) {
      s_was_connected = true;
      Serial.printf("[WiFi] Reconnected. IP=%s\n", WiFi.localIP().toString().c_str());
    }
    return;
  }

  if (s_was_connected) {
    s_was_connected = false;
    Serial.println(F("[WiFi] Disconnected."));
  }

  uint32_t now = millis();
  if (now - s_last_attempt_ms < 5000) {
    return;
  }
  s_last_attempt_ms = now;
  s_reconnect_count++;
  Serial.printf("[WiFi] Reconnect attempt #%lu\n", (unsigned long)s_reconnect_count);
  WiFi.disconnect();
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

bool wifi_is_connected() {
  return WiFi.status() == WL_CONNECTED;
}

String wifi_ip() {
  if (!wifi_is_connected()) {
    return String("0.0.0.0");
  }
  return WiFi.localIP().toString();
}

int wifi_rssi() {
  if (!wifi_is_connected()) {
    return 0;
  }
  return WiFi.RSSI();
}

uint32_t wifi_reconnect_count() {
  return s_reconnect_count;
}
