#pragma once

#include <stdint.h>

/*
 * Prototype BPM estimator — not clinically validated.
 * Educational / research use only.
 */

struct HeartRateResult {
  float bpm;          // NaN or <=0 means unavailable
  bool valid;
  const char *status; // "ok" | "insufficient_signal" | "warming_up"
};

void heart_rate_reset();
void heart_rate_configure(float min_bpm, float max_bpm);
HeartRateResult heart_rate_update(float envelope, float sample_rate, float signal_quality_score);
