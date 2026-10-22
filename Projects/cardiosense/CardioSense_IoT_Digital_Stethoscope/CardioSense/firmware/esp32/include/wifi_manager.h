#pragma once

#include <Arduino.h>

bool wifi_begin();
void wifi_loop();
bool wifi_is_connected();
String wifi_ip();
int wifi_rssi();
uint32_t wifi_reconnect_count();
