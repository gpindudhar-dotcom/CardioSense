#pragma once

#include <Arduino.h>
#include <stdint.h>
#include "signal_processing.h"

bool ws_server_begin();
void ws_server_loop();
void ws_broadcast_audio_packet(const int16_t *samples, size_t count, uint32_t seq,
                               float sample_rate, const ProcessedBlock &meta, float bpm);
bool ws_has_clients();
uint32_t ws_packets_sent();
