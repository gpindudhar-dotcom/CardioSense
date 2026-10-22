#include "audio_sampler.h"
#include "config.h"

#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/semphr.h>
#include <string.h>

/*
 * Continuous ADC sampling into a ring of BLOCK_SIZE frames.
 * Uses analogRead for broad ESP32-S3 board compatibility.
 * Default ADC_PIN=4 — change in config.h. Verify the exact board pinout before wiring.
 */

struct RingBlock {
  int16_t samples[BLOCK_SIZE];
  bool ready;
};

static RingBlock s_ring[RING_BUFFER_BLOCKS];
static volatile uint8_t s_write_idx = 0;
static volatile uint8_t s_read_idx = 0;
static volatile uint32_t s_total_samples = 0;
static volatile uint32_t s_dropped = 0;
static float s_adc_mid = 2048.0f;
static TaskHandle_t s_task = nullptr;
static portMUX_TYPE s_mux = portMUX_INITIALIZER_UNLOCKED;
static volatile bool s_running = false;

static void push_block(const int16_t *block) {
  portENTER_CRITICAL(&s_mux);
  uint8_t next = (uint8_t)((s_write_idx + 1) % RING_BUFFER_BLOCKS);
  if (next == s_read_idx) {
    s_dropped++;
    s_read_idx = (uint8_t)((s_read_idx + 1) % RING_BUFFER_BLOCKS);
  }
  memcpy(s_ring[s_write_idx].samples, block, BLOCK_SIZE * sizeof(int16_t));
  s_ring[s_write_idx].ready = true;
  s_write_idx = next;
  portEXIT_CRITICAL(&s_mux);
}

static void audio_task(void *param) {
  (void)param;
  const uint32_t period_us = 1000000UL / (uint32_t)SAMPLE_RATE;
  int16_t block[BLOCK_SIZE];
  uint16_t fill = 0;
  uint32_t next_us = micros();

  while (s_running) {
    uint32_t now = micros();
    int32_t delta = (int32_t)(next_us - now);
    if (delta > 50) {
      delayMicroseconds((uint32_t)delta - 20);
      continue;
    }
    if (delta < -((int32_t)period_us * 4)) {
      // Recover if we fell far behind
      next_us = now;
    }

    int raw = analogRead(ADC_PIN);
    if (raw < 0) raw = 0;
    if (raw > 4095) raw = 4095;
    block[fill++] = (int16_t)(raw - (int)s_adc_mid);
    s_total_samples++;
    next_us += period_us;

    if (fill >= BLOCK_SIZE) {
      push_block(block);
      fill = 0;
    }
  }
  vTaskDelete(nullptr);
}

bool audio_sampler_begin() {
  analogReadResolution(12);
  analogSetPinAttenuation(ADC_PIN, ADC_11db);
  pinMode(ADC_PIN, INPUT);

  uint32_t acc = 0;
  const int n = 256;
  for (int i = 0; i < n; i++) {
    acc += (uint32_t)analogRead(ADC_PIN);
    delayMicroseconds(200);
  }
  s_adc_mid = (float)acc / (float)n;
  Serial.printf("[ADC] GPIO%d mid=%.1f sample_rate=%d block=%d\n",
                ADC_PIN, s_adc_mid, SAMPLE_RATE, BLOCK_SIZE);

  for (int i = 0; i < RING_BUFFER_BLOCKS; i++) {
    s_ring[i].ready = false;
  }

  s_running = true;
  BaseType_t ok = xTaskCreatePinnedToCore(
      audio_task, "audio_sampler", 4096, nullptr, 2, &s_task, 0);
  if (ok != pdPASS) {
    s_running = false;
    Serial.println(F("[ADC] Failed to create sampler task"));
    return false;
  }
  return true;
}

void audio_sampler_loop() {
  // Sampling runs in FreeRTOS task.
}

bool audio_sampler_pop_block(int16_t *out, size_t count) {
  if (count != BLOCK_SIZE || out == nullptr) {
    return false;
  }
  bool ok = false;
  portENTER_CRITICAL(&s_mux);
  if (s_read_idx != s_write_idx && s_ring[s_read_idx].ready) {
    memcpy(out, s_ring[s_read_idx].samples, BLOCK_SIZE * sizeof(int16_t));
    s_ring[s_read_idx].ready = false;
    s_read_idx = (uint8_t)((s_read_idx + 1) % RING_BUFFER_BLOCKS);
    ok = true;
  }
  portEXIT_CRITICAL(&s_mux);
  return ok;
}

uint32_t audio_sampler_total_samples() {
  return s_total_samples;
}

uint32_t audio_sampler_dropped_blocks() {
  return s_dropped;
}

float audio_sampler_adc_mid() {
  return s_adc_mid;
}
