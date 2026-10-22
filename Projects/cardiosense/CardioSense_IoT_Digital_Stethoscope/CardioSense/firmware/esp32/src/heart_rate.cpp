#include "heart_rate.h"
#include "config.h"

#include <math.h>
#include <string.h>

/*
 * Prototype heart-rate estimate from envelope peaks.
 * NOT clinically validated. Educational use only.
 */

static float s_min_bpm = 40.0f;
static float s_max_bpm = 180.0f;
static float s_prev_env = 0.0f;
static float s_prev_deriv = 0.0f;
static float s_threshold = 30.0f;
static float s_threshold_ema = 30.0f;
static uint32_t s_sample_index = 0;
static uint32_t s_last_peak_index = 0;
static float s_intervals[8];
static int s_interval_count = 0;
static float s_bpm_smooth = 0.0f;
static bool s_have_bpm = false;
static uint32_t s_samples_since_peak = 0;

void heart_rate_reset() {
  s_prev_env = 0.0f;
  s_prev_deriv = 0.0f;
  s_threshold = 30.0f;
  s_threshold_ema = 30.0f;
  s_sample_index = 0;
  s_last_peak_index = 0;
  memset(s_intervals, 0, sizeof(s_intervals));
  s_interval_count = 0;
  s_bpm_smooth = 0.0f;
  s_have_bpm = false;
  s_samples_since_peak = 0;
}

void heart_rate_configure(float min_bpm, float max_bpm) {
  if (min_bpm > 0.0f && max_bpm > min_bpm) {
    s_min_bpm = min_bpm;
    s_max_bpm = max_bpm;
  }
}

static bool interval_ok(float seconds) {
  float min_s = 60.0f / s_max_bpm;
  float max_s = 60.0f / s_min_bpm;
  return seconds >= min_s && seconds <= max_s;
}

static float average_intervals() {
  if (s_interval_count <= 0) {
    return 0.0f;
  }
  float sum = 0.0f;
  for (int i = 0; i < s_interval_count; i++) {
    sum += s_intervals[i];
  }
  return sum / (float)s_interval_count;
}

HeartRateResult heart_rate_update(float envelope, float sample_rate, float signal_quality_score) {
  HeartRateResult result{};
  result.bpm = 0.0f;
  result.valid = false;
  result.status = "insufficient_signal";

  // Approximate per-sample advance assuming one call per block with its mean envelope.
  const uint32_t block_advance = BLOCK_SIZE;
  s_sample_index += block_advance;
  s_samples_since_peak += block_advance;

  if (signal_quality_score < 0.35f) {
    s_have_bpm = false;
    s_interval_count = 0;
    result.status = "insufficient_signal";
    return result;
  }

  // Adaptive threshold from envelope EMA
  s_threshold_ema = 0.95f * s_threshold_ema + 0.05f * (envelope * 1.4f + 10.0f);
  s_threshold = s_threshold_ema;
  if (s_threshold < 15.0f) {
    s_threshold = 15.0f;
  }

  float deriv = envelope - s_prev_env;
  bool peak = (s_prev_deriv > 0.0f && deriv <= 0.0f && s_prev_env > s_threshold);

  // Refractory period ~ 60/max_bpm
  uint32_t min_samples = (uint32_t)(sample_rate * (60.0f / s_max_bpm));
  if (peak && s_samples_since_peak >= min_samples) {
    if (s_last_peak_index > 0) {
      float interval_s = (float)(s_sample_index - s_last_peak_index) / sample_rate;
      if (interval_ok(interval_s)) {
        if (s_interval_count < 8) {
          s_intervals[s_interval_count++] = interval_s;
        } else {
          for (int i = 1; i < 8; i++) {
            s_intervals[i - 1] = s_intervals[i];
          }
          s_intervals[7] = interval_s;
        }
      }
    }
    s_last_peak_index = s_sample_index;
    s_samples_since_peak = 0;
  }

  s_prev_env = envelope;
  s_prev_deriv = deriv;

  if (s_interval_count >= 3) {
    float mean_i = average_intervals();
    if (mean_i > 0.0f) {
      float bpm = 60.0f / mean_i;
      if (bpm >= s_min_bpm && bpm <= s_max_bpm) {
        if (!s_have_bpm) {
          s_bpm_smooth = bpm;
          s_have_bpm = true;
        } else {
          s_bpm_smooth = 0.8f * s_bpm_smooth + 0.2f * bpm;
        }
        result.bpm = s_bpm_smooth;
        result.valid = true;
        result.status = "ok";
        return result;
      }
    }
  }

  if (s_sample_index < (uint32_t)(sample_rate * 3)) {
    result.status = "warming_up";
  } else {
    result.status = "insufficient_signal";
  }
  return result;
}
