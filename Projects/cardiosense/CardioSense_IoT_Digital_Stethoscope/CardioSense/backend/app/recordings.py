"""WAV recording helpers for CardioSense."""

from __future__ import annotations

import struct
import wave
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np


def float_samples_to_int16(samples: Sequence[float]) -> np.ndarray:
    arr = np.asarray(list(samples), dtype=float)
    if arr.size == 0:
        return np.zeros(0, dtype=np.int16)
    peak = float(np.max(np.abs(arr))) if arr.size else 0.0
    if peak < 1e-9:
        return np.zeros(arr.shape, dtype=np.int16)
    # If already in ADC-ish range, scale to int16 full-ish range without clipping badly
    if peak <= 1.0:
        scaled = arr * 32767.0
    elif peak <= 2048.0:
        scaled = (arr / 2048.0) * 30000.0
    else:
        scaled = (arr / peak) * 30000.0
    return np.clip(scaled, -32767, 32767).astype(np.int16)


def write_wav(path: Path, samples: Sequence[float], sample_rate: int = 4000) -> dict:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = float_samples_to_int16(samples)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(int(sample_rate))
        wf.writeframes(pcm.tobytes())
    duration = float(pcm.size) / float(sample_rate) if sample_rate else 0.0
    return {
        "filename": path.name,
        "sample_count": int(pcm.size),
        "duration_sec": duration,
        "sample_rate": int(sample_rate),
        "path": str(path),
    }


def read_wav_samples(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wf:
        rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
        sampwidth = wf.getsampwidth()
        nch = wf.getnchannels()
    if sampwidth == 2:
        data = np.frombuffer(frames, dtype=np.int16).astype(float)
    elif sampwidth == 1:
        data = np.frombuffer(frames, dtype=np.uint8).astype(float) - 128.0
    else:
        data = np.frombuffer(frames, dtype=np.int16).astype(float)
    if nch > 1:
        data = data.reshape(-1, nch)[:, 0]
    return data, int(rate)


def build_wav_bytes(samples: Iterable[float], sample_rate: int = 4000) -> bytes:
    pcm = float_samples_to_int16(list(samples))
    n = pcm.size
    data_size = n * 2
    # RIFF WAV header (PCM 16-bit mono)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        int(sample_rate),
        int(sample_rate) * 2,
        2,
        16,
        b"data",
        data_size,
    )
    return header + pcm.tobytes()
