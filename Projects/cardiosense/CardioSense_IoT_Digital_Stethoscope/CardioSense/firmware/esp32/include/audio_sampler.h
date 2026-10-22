#pragma once

#include <Arduino.h>
#include <stddef.h>
#include <stdint.h>
#include "config.h"

bool audio_sampler_begin();
void audio_sampler_loop();
bool audio_sampler_pop_block(int16_t *out, size_t count);
uint32_t audio_sampler_total_samples();
uint32_t audio_sampler_dropped_blocks();
float audio_sampler_adc_mid();
