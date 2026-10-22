"""
CardioSense signal processing (Python).

Educational prototype DSP — not clinically validated.
Does not diagnose disease.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

import numpy as np
from scipy.signal import butter, filtfilt, find_peaks, hilbert


QUALITY_LABELS = ["No Signal", "Poor", "Fair", "Good", "Excellent"]


@dataclass
class HeartRateResult:
    bpm: Optional[float]
    valid: bool
    status: str  # ok | insufficient_signal | warming_up


@dataclass
class QualityResult:
    score: int  # 0..4
    label: str
    rms: float
    peak: float
    clipping_ratio: float
    noise_floor: float
    band_energy_ratio: float


def moving_average(x: np.ndarray, window: int = 16) -> np.ndarray:
    if window <= 1 or x.size == 0:
        return np.asarray(x, dtype=float)
    kernel = np.ones(window, dtype=float) / float(window)
    return np.convolve(x, kernel, mode="same")


def high_pass(x: np.ndarray, cutoff_hz: float, sample_rate: float, order: int = 2) -> np.ndarray:
    if x.size < 12:
        return np.asarray(x, dtype=float)
    nyq = 0.5 * sample_rate
    wn = min(max(cutoff_hz / nyq, 1e-4), 0.99)
    b, a = butter(order, wn, btype="high")
    return filtfilt(b, a, x)


def low_pass(x: np.ndarray, cutoff_hz: float, sample_rate: float, order: int = 2) -> np.ndarray:
    if x.size < 12:
        return np.asarray(x, dtype=float)
    nyq = 0.5 * sample_rate
    wn = min(max(cutoff_hz / nyq, 1e-4), 0.99)
    b, a = butter(order, wn, btype="low")
    return filtfilt(b, a, x)


def band_pass(
    x: np.ndarray,
    low_hz: float = 20.0,
    high_hz: float = 400.0,
    sample_rate: float = 4000.0,
    order: int = 2,
) -> np.ndarray:
    y = high_pass(np.asarray(x, dtype=float), low_hz, sample_rate, order)
    y = low_pass(y, high_hz, sample_rate, order)
    return y


def remove_dc(x: np.ndarray) -> np.ndarray:
    arr = np.asarray(x, dtype=float)
    if arr.size == 0:
        return arr
    return arr - np.mean(arr)


def rms(x: np.ndarray) -> float:
    arr = np.asarray(x, dtype=float)
    if arr.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(arr * arr)))


def peak_amplitude(x: np.ndarray) -> float:
    arr = np.asarray(x, dtype=float)
    if arr.size == 0:
        return 0.0
    return float(np.max(np.abs(arr)))


def envelope(x: np.ndarray) -> np.ndarray:
    arr = np.asarray(x, dtype=float)
    if arr.size < 4:
        return np.abs(arr)
    analytic = hilbert(arr)
    env = np.abs(analytic)
    return moving_average(env, window=max(8, arr.size // 200))


def detect_peaks(
    env: np.ndarray,
    sample_rate: float,
    min_bpm: float = 40.0,
    max_bpm: float = 180.0,
) -> np.ndarray:
    if env.size == 0:
        return np.array([], dtype=int)
    min_distance = max(1, int(sample_rate * (60.0 / max_bpm)))
    height = max(float(np.mean(env) * 1.2), float(np.percentile(env, 60)))
    peaks, _ = find_peaks(env, distance=min_distance, height=height, prominence=height * 0.2)
    return peaks


def estimate_bpm(
    samples: Iterable[float],
    sample_rate: float = 4000.0,
    min_bpm: float = 40.0,
    max_bpm: float = 180.0,
    min_intervals: int = 3,
) -> HeartRateResult:
    """
    Prototype estimate – not clinically validated.
    """
    x = remove_dc(np.asarray(list(samples), dtype=float))
    if x.size < int(sample_rate * 2):
        return HeartRateResult(None, False, "warming_up")

    filtered = band_pass(x, 20.0, 400.0, sample_rate)
    env = envelope(filtered)
    q = assess_signal_quality(filtered, sample_rate)
    if q.score < 2:
        return HeartRateResult(None, False, "insufficient_signal")

    peaks = detect_peaks(env, sample_rate, min_bpm, max_bpm)
    if peaks.size < (min_intervals + 1):
        return HeartRateResult(None, False, "insufficient_signal")

    intervals = np.diff(peaks) / float(sample_rate)
    min_s = 60.0 / max_bpm
    max_s = 60.0 / min_bpm
    good = intervals[(intervals >= min_s) & (intervals <= max_s)]
    if good.size < min_intervals:
        return HeartRateResult(None, False, "insufficient_signal")

    # Reject outlier intervals (noisy peaks)
    med = float(np.median(good))
    filtered_intervals = good[np.abs(good - med) <= 0.35 * med]
    if filtered_intervals.size < min_intervals:
        return HeartRateResult(None, False, "insufficient_signal")

    bpm = 60.0 / float(np.mean(filtered_intervals))
    if bpm < min_bpm or bpm > max_bpm:
        return HeartRateResult(None, False, "insufficient_signal")

    # Smooth lightly toward median instantaneous BPM
    inst = 60.0 / filtered_intervals
    bpm_smooth = float(0.7 * np.median(inst) + 0.3 * bpm)
    return HeartRateResult(bpm_smooth, True, "ok")


def assess_signal_quality(samples: Iterable[float], sample_rate: float = 4000.0) -> QualityResult:
    x = np.asarray(list(samples), dtype=float)
    if x.size == 0:
        return QualityResult(0, QUALITY_LABELS[0], 0.0, 0.0, 0.0, 0.0, 0.0)

    x = remove_dc(x)
    r = rms(x)
    p = peak_amplitude(x)
    var = float(np.var(x))
    clip_lim = 0.95 * max(p, 1.0)
    # For int16-ish ranges use absolute clip near 2000
    abs_clip = np.mean(np.abs(x) > 1900.0)
    noise = float(np.percentile(np.abs(x), 20)) if x.size else 0.0

    # Usable band energy ratio via FFT
    band_ratio = 0.0
    if x.size >= 64:
        spec = np.fft.rfft(x * np.hanning(x.size))
        freqs = np.fft.rfftfreq(x.size, d=1.0 / sample_rate)
        power = np.abs(spec) ** 2
        total = float(np.sum(power)) + 1e-12
        band = (freqs >= 20.0) & (freqs <= 400.0)
        band_ratio = float(np.sum(power[band]) / total)

    score = 0
    if r < 5.0 and p < 20.0:
        score = 0
    else:
        snr_proxy = r / max(noise, 1.0)
        if abs_clip > 0.02:
            score = 1
        elif r < 15.0 or var < 40.0 or band_ratio < 0.15:
            score = 1
        elif snr_proxy > 8.0 and 80.0 < p < 1600.0 and band_ratio > 0.45:
            score = 4
        elif snr_proxy > 4.0 and band_ratio > 0.3:
            score = 3
        elif snr_proxy > 2.0:
            score = 2
        else:
            score = 1

    return QualityResult(
        score=score,
        label=QUALITY_LABELS[score],
        rms=r,
        peak=p,
        clipping_ratio=float(abs_clip),
        noise_floor=noise,
        band_energy_ratio=band_ratio,
    )


def process_pipeline(samples: Iterable[float], sample_rate: float = 4000.0) -> dict:
    x = remove_dc(np.asarray(list(samples), dtype=float))
    filtered = band_pass(x, 20.0, 400.0, sample_rate)
    env = envelope(filtered)
    quality = assess_signal_quality(filtered, sample_rate)
    hr = estimate_bpm(filtered, sample_rate)
    return {
        "filtered": filtered.tolist(),
        "envelope": env.tolist(),
        "rms": quality.rms,
        "peak": quality.peak,
        "quality": quality.label,
        "quality_score": quality.score,
        "bpm": hr.bpm if hr.valid else None,
        "bpm_status": hr.status,
        "notice": "Prototype estimate – not clinically validated.",
    }


def spectrum(samples: Iterable[float], sample_rate: float = 4000.0) -> dict:
    x = remove_dc(np.asarray(list(samples), dtype=float))
    if x.size < 8:
        return {"freqs": [], "magnitude": []}
    windowed = x * np.hanning(x.size)
    mag = np.abs(np.fft.rfft(windowed))
    freqs = np.fft.rfftfreq(x.size, d=1.0 / sample_rate)
    # Downsample spectrum for UI if large
    if freqs.size > 512:
        idx = np.linspace(0, freqs.size - 1, 512).astype(int)
        freqs = freqs[idx]
        mag = mag[idx]
    return {"freqs": freqs.tolist(), "magnitude": mag.tolist()}
