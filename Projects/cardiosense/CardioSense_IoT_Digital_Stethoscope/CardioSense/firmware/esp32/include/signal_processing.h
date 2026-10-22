#pragma once

#include <stddef.h>
#include <stdint.h>

struct ProcessedBlock {
  float rms;
  float peak;
  float dc_offset;
  float envelope;
  uint8_t quality; // 0=no signal .. 4=excellent
};

void dsp_reset();
void dsp_process_block(const int16_t *in, int16_t *out, size_t n, float sample_rate, ProcessedBlock *meta);
float dsp_high_pass(float x, float cutoff_hz, float sample_rate);
float dsp_low_pass(float x, float cutoff_hz, float sample_rate);
