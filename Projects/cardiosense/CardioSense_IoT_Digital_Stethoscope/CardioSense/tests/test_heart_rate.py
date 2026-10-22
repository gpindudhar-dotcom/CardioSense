"""Heart-rate algorithm unit tests."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.signal_processing import estimate_bpm


def _pulse_train(sr: float, bpm: float, seconds: float, amp: float = 600.0, seed: int = 2):
    period = 60.0 / bpm
    t = np.arange(0, seconds, 1 / sr)
    x = np.zeros_like(t)
    for k in range(int(seconds / period)):
        c = 0.25 + k * period
        env = np.exp(-((t - c) ** 2) / (2 * (0.018**2)))
        x += amp * env * np.sin(2 * np.pi * 55 * t)
    x += np.random.default_rng(seed).normal(scale=8.0, size=x.size)
    return x


def test_rejects_unrealistic_output_range():
    """Configured max_bpm must bound any accepted estimate."""
    sr = 4000
    x = _pulse_train(sr, bpm=72, seconds=8, amp=700)
    r = estimate_bpm(x, sr, min_bpm=40, max_bpm=180)
    assert r.valid
    assert 40 <= r.bpm <= 180


def test_rejects_sparse_noisy_peaks():
    """Sparse noise without repeating heart-sound structure → insufficient."""
    sr = 4000
    rng = np.random.default_rng(9)
    x = rng.normal(scale=3.0, size=int(sr * 6))
    # A couple of unrelated impulses (not a regular train)
    x[1000] = 800
    x[4500] = 800
    r = estimate_bpm(x, sr, min_bpm=40, max_bpm=180)
    assert r.valid is False
    assert r.bpm is None


def test_averages_multiple_intervals():
    sr = 4000
    x = _pulse_train(sr, bpm=60, seconds=10, amp=650)
    r = estimate_bpm(x, sr, min_bpm=40, max_bpm=180, min_intervals=3)
    assert r.valid
    assert 50 <= r.bpm <= 70


def test_short_signal_warming_up():
    sr = 4000
    x = _pulse_train(sr, bpm=72, seconds=1.0)
    r = estimate_bpm(x, sr)
    assert r.valid is False
    assert r.status == "warming_up"
