#include "signal_processing.h"
#include "config.h"

#include <math.h>
#include <string.h>

static float s_hp_prev_x = 0.0f;
static float s_hp_prev_y = 0.0f;
static float s_lp_y = 0.0f;
static float s_ma_buf[16];
static int s_ma_idx = 0;
static float s_ma_sum = 0.0f;
static bool s_ma_filled = false;
static float s_noise_ema = 0.0f;

void dsp_reset() {
  s_hp_prev_x = 0.0f;
  s_hp_prev_y = 0.0f;
  s_lp_y = 0.0f;
  memset(s_ma_buf, 0, sizeof(s_ma_buf));
  s_ma_idx = 0;
  s_ma_sum = 0.0f;
  s_ma_filled = false;
  s_noise_ema = 0.0f;
}

float dsp_high_pass(float x, float cutoff_hz, float sample_rate) {
  float rc = 1.0f / (2.0f * 3.14159265f * cutoff_hz);
  float dt = 1.0f / sample_rate;
  float alpha = rc / (rc + dt);
  float y = alpha * (s_hp_prev_y + x - s_hp_prev_x);
  s_hp_prev_x = x;
  s_hp_prev_y = y;
  return y;
}

float dsp_low_pass(float x, float cutoff_hz, float sample_rate) {
  float rc = 1.0f / (2.0f * 3.14159265f * cutoff_hz);
  float dt = 1.0f / sample_rate;
  float alpha = dt / (rc + dt);
  s_lp_y = s_lp_y + alpha * (x - s_lp_y);
  return s_lp_y;
}

static float moving_average(float x) {
  s_ma_sum -= s_ma_buf[s_ma_idx];
  s_ma_buf[s_ma_idx] = x;
  s_ma_sum += x;
  s_ma_idx = (s_ma_idx + 1) % 16;
  if (s_ma_idx == 0) {
    s_ma_filled = true;
  }
  float n = s_ma_filled ? 16.0f : (float)(s_ma_idx == 0 ? 16 : s_ma_idx);
  return s_ma_sum / n;
}

static uint8_t estimate_quality(float rms, float peak, float variance) {
  // Heuristic quality for educational prototype (not clinical).
  if (rms < 5.0f && peak < 20.0f) {
    return 0; // no signal
  }
  bool clipping = peak > 1800.0f;
  float snr_proxy = (s_noise_ema > 1.0f) ? (rms / s_noise_ema) : rms;
  if (clipping) {
    return 1; // poor
  }
  if (rms < 20.0f || variance < 50.0f) {
    return 1;
  }
  if (snr_proxy > 8.0f && peak > 80.0f && peak < 1500.0f) {
    return 4;
  }
  if (snr_proxy > 4.0f) {
    return 3;
  }
  if (snr_proxy > 2.0f) {
    return 2;
  }
  return 1;
}

void dsp_process_block(const int16_t *in, int16_t *out, size_t n, float sample_rate, ProcessedBlock *meta) {
  double sum = 0.0;
  double sumsq = 0.0;
  float peak = 0.0f;
  float env_acc = 0.0f;

  for (size_t i = 0; i < n; i++) {
    float x = (float)in[i];
    // DC removal via HPF, then LPF → band-pass for heart-sound band
    float y = dsp_high_pass(x, HPF_CUTOFF_HZ, sample_rate);
    y = dsp_low_pass(y, LPF_CUTOFF_HZ, sample_rate);
    // Light noise reduction / smoothing
    y = moving_average(y);

    if (y > 2000.0f) y = 2000.0f;
    if (y < -2000.0f) y = -2000.0f;
    out[i] = (int16_t)lroundf(y);

    float ay = fabsf(y);
    if (ay > peak) peak = ay;
    sum += y;
    sumsq += (double)y * (double)y;
    env_acc += ay;
  }

  float mean = (float)(sum / (double)n);
  float rms = (float)sqrt(sumsq / (double)n);
  float variance = (float)(sumsq / (double)n) - mean * mean;
  if (variance < 0.0f) variance = 0.0f;

  // Noise floor EMA from quieter samples
  float quiet = rms;
  s_noise_ema = 0.95f * s_noise_ema + 0.05f * quiet;

  float envelope = env_acc / (float)n;
  envelope = 0.7f * envelope + 0.3f * peak; // blend for event detection

  if (meta) {
    meta->rms = rms;
    meta->peak = peak;
    meta->dc_offset = mean;
    meta->envelope = envelope;
    meta->quality = estimate_quality(rms, peak, variance);
  }
}
