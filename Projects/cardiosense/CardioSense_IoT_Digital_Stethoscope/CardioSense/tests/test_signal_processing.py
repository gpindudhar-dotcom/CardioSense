"""Unit tests for CardioSense DSP helpers."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.recordings import build_wav_bytes, float_samples_to_int16, write_wav
from app.signal_processing import (
    assess_signal_quality,
    band_pass,
    estimate_bpm,
    high_pass,
    low_pass,
    moving_average,
    peak_amplitude,
    remove_dc,
    rms,
)


def test_remove_dc():
    x = np.array([1.0, 2.0, 3.0, 4.0])
    y = remove_dc(x)
    assert abs(np.mean(y)) < 1e-9


def test_moving_average_smooths():
    x = np.array([0.0, 10.0, 0.0, 10.0, 0.0, 10.0], dtype=float)
    y = moving_average(x, window=3)
    assert y.shape == x.shape
    assert np.std(y) < np.std(x)


def test_filters_preserve_length():
    sr = 4000
    t = np.arange(0, 1.0, 1 / sr)
    x = np.sin(2 * np.pi * 50 * t)
    hp = high_pass(x, 20, sr)
    lp = low_pass(x, 200, sr)
    bp = band_pass(x, 20, 200, sr)
    assert len(hp) == len(x)
    assert len(lp) == len(x)
    assert len(bp) == len(x)


def test_rms_and_peak():
    x = np.array([3.0, -4.0, 0.0])
    assert abs(rms(x) - 2.5) < 1e-9 or abs(rms(x) - math.sqrt((9 + 16) / 3)) < 1e-9
    assert peak_amplitude(x) == 4.0


def test_signal_quality_no_signal():
    q = assess_signal_quality(np.zeros(2000), 4000)
    assert q.label == "No Signal"
    assert q.score == 0


def test_signal_quality_strong_tone():
    sr = 4000
    t = np.arange(0, 2.0, 1 / sr)
    x = 400 * np.sin(2 * np.pi * 80 * t)
    q = assess_signal_quality(x, sr)
    assert q.score >= 2
    assert q.label in {"Fair", "Good", "Excellent"}


def test_wav_generation(tmp_path):
    samples = [0.0, 0.5, -0.5, 0.25, -0.25] * 100
    path = tmp_path / "t.wav"
    meta = write_wav(path, samples, 4000)
    assert path.exists()
    assert meta["sample_count"] == len(samples)
    raw = build_wav_bytes(samples, 4000)
    assert raw[:4] == b"RIFF"
    assert raw[8:12] == b"WAVE"
    pcm = float_samples_to_int16(samples)
    assert pcm.dtype == np.int16
    assert pcm.size == len(samples)


@pytest.fixture()
def synthetic_heartbeat():
    """Synthetic envelope pulses at 72 BPM for algorithm testing (not clinical data)."""
    sr = 4000
    duration = 8.0
    bpm = 72.0
    period = 60.0 / bpm
    t = np.arange(0, duration, 1 / sr)
    x = np.zeros_like(t)
    # Narrow tone bursts (proxy heart-sound events)
    for k in range(int(duration / period)):
        center = k * period + 0.2
        burst = np.exp(-((t - center) ** 2) / (2 * (0.02**2))) * np.sin(2 * np.pi * 60 * t)
        x += 500 * burst
    x += 5 * np.random.default_rng(0).normal(size=x.size)
    return x, sr, bpm


def test_bpm_estimate_near_synthetic(synthetic_heartbeat):
    x, sr, true_bpm = synthetic_heartbeat
    result = estimate_bpm(x, sr, min_bpm=40, max_bpm=180)
    assert result.valid
    assert result.bpm is not None
    assert abs(result.bpm - true_bpm) < 12.0


def test_bpm_insufficient_on_noise():
    rng = np.random.default_rng(1)
    x = rng.normal(scale=2.0, size=8000)
    result = estimate_bpm(x, 4000)
    assert result.valid is False
    assert result.bpm is None
    assert result.status in {"insufficient_signal", "warming_up"}
