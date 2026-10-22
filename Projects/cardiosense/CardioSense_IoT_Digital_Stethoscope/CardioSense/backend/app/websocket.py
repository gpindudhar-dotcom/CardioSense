"""
WebSocket audio bridge for CardioSense.

Binary packet format (little-endian) — must match firmware:
Offset  Size  Field
0       4     magic = 0x44534E43 ('CSND')
4       1     version
5       1     flags
6       2     sample_count
8       4     sequence
12      4     sample_rate (float32)
16      4     rms (float32)
20      4     peak (float32)
24      4     bpm (float32, NaN if invalid)
28      1     quality 0-4
29      3     reserved
32      2*N   int16 samples
"""

from __future__ import annotations

import asyncio
import json
import math
import struct
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import WebSocket, WebSocketDisconnect

from .signal_processing import QUALITY_LABELS, assess_signal_quality, estimate_bpm, spectrum

PACKET_MAGIC = 0x44534E43
HEADER_SIZE = 32


@dataclass
class LiveState:
    connected: bool = False
    device_id: str = "unknown"
    ip: Optional[str] = None
    rssi: Optional[int] = None
    sample_rate: int = 4000
    packets_received: int = 0
    last_seen: Optional[datetime] = None
    wifi_connected: bool = False
    bpm: Optional[float] = None
    signal_quality: str = "No Signal"
    rms: float = 0.0
    peak: float = 0.0
    recent_samples: list[float] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "connected": self.connected,
            "device_id": self.device_id,
            "ip": self.ip,
            "rssi": self.rssi,
            "sample_rate": self.sample_rate,
            "packets_received": self.packets_received,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "wifi_connected": self.wifi_connected,
            "bpm": self.bpm,
            "signal_quality": self.signal_quality,
            "rms": self.rms,
            "peak": self.peak,
            "notice": "Educational prototype — not a medical diagnostic device.",
        }


class AudioHub:
    def __init__(self) -> None:
        self.state = LiveState()
        self.clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._bpm_window: list[float] = []
        self._max_window = 16000  # 4 seconds at 4 kHz

    async def register(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self.clients.add(ws)
        await ws.send_json({"type": "hello", "notice": "Educational prototype — not a medical diagnostic device."})
        await ws.send_json({"type": "device_status", "data": self.state.to_dict()})

    async def unregister(self, ws: WebSocket) -> None:
        async with self._lock:
            self.clients.discard(ws)

    async def broadcast(self, message: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        async with self._lock:
            clients = list(self.clients)
        for ws in clients:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.unregister(ws)

    async def broadcast_bytes(self, data: bytes) -> None:
        dead: list[WebSocket] = []
        async with self._lock:
            clients = list(self.clients)
        for ws in clients:
            try:
                await ws.send_bytes(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.unregister(ws)

    def legacy_sample(self, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        if "sample" not in data:
            return None
        try:
            sample = float(data["sample"])
            sample_rate = int(data.get("sample_rate", self.state.sample_rate))
            rms = float(data.get("rms", self.state.rms))
            peak = float(data.get("peak", self.state.peak))
            bpm_value = data.get("bpm")
            bpm = float(bpm_value) if bpm_value is not None else None
            sequence = int(data.get("sequence", self.state.packets_received))
        except (TypeError, ValueError, OverflowError):
            return None
        if (
            not all(math.isfinite(value) for value in (sample, rms, peak))
            or (bpm is not None and (not math.isfinite(bpm) or bpm <= 0))
            or sample_rate <= 0
        ):
            return None

        quality = data.get("quality", "No Signal")
        if isinstance(quality, int):
            quality = QUALITY_LABELS[quality] if 0 <= quality < len(QUALITY_LABELS) else "Unknown"
        return {
            "sequence": sequence,
            "sample_rate": sample_rate,
            "rms": rms,
            "peak": peak,
            "bpm": bpm,
            "quality": str(quality),
            "samples": [sample],
        }

    def parse_packet(self, data: bytes) -> Optional[dict[str, Any]]:
        if data is None or len(data) < HEADER_SIZE:
            return None
        try:
            magic = struct.unpack_from("<I", data, 0)[0]
            version = data[4]
            flags = data[5]
            count = struct.unpack_from("<H", data, 6)[0]
            seq = struct.unpack_from("<I", data, 8)[0]
            sr = struct.unpack_from("<f", data, 12)[0]
            rms = struct.unpack_from("<f", data, 16)[0]
            peak = struct.unpack_from("<f", data, 20)[0]
            bpm = struct.unpack_from("<f", data, 24)[0]
            quality = data[28]
        except struct.error:
            return None

        if magic != PACKET_MAGIC:
            return None
        if count <= 0 or count > 8192:
            return None
        expected = HEADER_SIZE + count * 2
        if len(data) < expected:
            return None

        samples = list(struct.unpack_from(f"<{count}h", data, HEADER_SIZE))
        bpm_val: Optional[float]
        if bpm is None or (isinstance(bpm, float) and (math.isnan(bpm) or math.isinf(bpm) or bpm <= 0)):
            bpm_val = None
        else:
            bpm_val = float(bpm)

        q_label = QUALITY_LABELS[quality] if 0 <= quality < len(QUALITY_LABELS) else "Unknown"
        return {
            "version": version,
            "flags": flags,
            "count": count,
            "sequence": seq,
            "sample_rate": int(sr) if sr > 0 else 4000,
            "rms": float(rms),
            "peak": float(peak),
            "bpm": bpm_val,
            "quality": q_label,
            "quality_score": int(quality),
            "samples": samples,
        }

    async def handle_device_packet(self, data: bytes) -> None:
        parsed = self.parse_packet(data)
        if not parsed:
            await self.broadcast({"type": "error", "message": "Malformed audio packet ignored."})
            return

        samples = [float(s) for s in parsed["samples"]]
        self.state.connected = True
        self.state.packets_received += 1
        self.state.last_seen = datetime.now(timezone.utc)
        self.state.sample_rate = parsed["sample_rate"]
        self.state.rms = parsed["rms"]
        self.state.peak = parsed["peak"]
        self.state.signal_quality = parsed["quality"]

        self._bpm_window.extend(samples)
        if len(self._bpm_window) > self._max_window:
            self._bpm_window = self._bpm_window[-self._max_window :]

        # Prefer firmware BPM if present; refine with backend when window is long enough
        bpm = parsed["bpm"]
        if len(self._bpm_window) >= self.state.sample_rate * 3:
            q = assess_signal_quality(self._bpm_window, float(self.state.sample_rate))
            self.state.signal_quality = q.label
            self.state.rms = q.rms
            self.state.peak = q.peak
            hr = estimate_bpm(self._bpm_window, float(self.state.sample_rate))
            if hr.valid:
                bpm = hr.bpm
            elif q.score < 2:
                bpm = None
        self.state.bpm = bpm

        # Keep a short recent buffer for spectrum endpoints
        self.state.recent_samples = (self.state.recent_samples + samples)[-4096:]

        payload = {
            "type": "audio",
            "sequence": parsed["sequence"],
            "sample_rate": parsed["sample_rate"],
            "rms": self.state.rms,
            "peak": self.state.peak,
            "bpm": self.state.bpm,
            "bpm_note": "Prototype estimate – not clinically validated.",
            "signal_quality": self.state.signal_quality,
            "samples": samples,
            "packets_received": self.state.packets_received,
        }
        await self.broadcast(payload)

        if self.state.packets_received % 10 == 0:
            await self.broadcast({"type": "device_status", "data": self.state.to_dict()})

    async def handle_legacy_sample(self, data: dict[str, Any]) -> None:
        parsed = self.legacy_sample(data)
        if not parsed:
            return
        self.state.connected = True
        self.state.packets_received += 1
        self.state.last_seen = datetime.now(timezone.utc)
        self.state.sample_rate = parsed["sample_rate"]
        self.state.rms = parsed["rms"]
        self.state.peak = parsed["peak"]
        self.state.bpm = parsed["bpm"]
        self.state.signal_quality = parsed["quality"]
        self.state.recent_samples = (self.state.recent_samples + parsed["samples"])[-4096:]
        await self.broadcast(
            {
                "type": "audio",
                "sequence": parsed["sequence"],
                "sample_rate": parsed["sample_rate"],
                "rms": parsed["rms"],
                "peak": parsed["peak"],
                "bpm": parsed["bpm"],
                "bpm_note": "Prototype estimate – not clinically validated.",
                "signal_quality": parsed["quality"],
                "samples": parsed["samples"],
                "packets_received": self.state.packets_received,
            }
        )

    async def handle_client_message(self, ws: WebSocket, message: str) -> None:
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            await ws.send_json({"type": "error", "message": "Invalid JSON message."})
            return

        mtype = data.get("type")
        if mtype == "ping":
            await ws.send_json({"type": "pong", "ts": time.time()})
        elif mtype == "get_status":
            await ws.send_json({"type": "device_status", "data": self.state.to_dict()})
        elif mtype == "get_spectrum":
            spec = spectrum(self.state.recent_samples, float(self.state.sample_rate))
            await ws.send_json({"type": "spectrum", "data": spec})
        elif mtype == "device_status_update":
            # Optional JSON status from a device bridge
            self.state.device_id = data.get("device_id", self.state.device_id)
            self.state.ip = data.get("ip", self.state.ip)
            self.state.rssi = data.get("rssi", self.state.rssi)
            self.state.wifi_connected = bool(data.get("wifi_connected", self.state.wifi_connected))
            self.state.connected = True
            self.state.last_seen = datetime.now(timezone.utc)
            await self.broadcast({"type": "device_status", "data": self.state.to_dict()})
        else:
            await ws.send_json({"type": "error", "message": f"Unknown message type: {mtype}"})


hub = AudioHub()


async def audio_websocket_endpoint(websocket: WebSocket) -> None:
    await hub.register(websocket)
    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break
            if "bytes" in message and message["bytes"] is not None:
                await hub.handle_device_packet(message["bytes"])
            elif "text" in message and message["text"] is not None:
                await hub.handle_client_message(websocket, message["text"])
    except WebSocketDisconnect:
        pass
    finally:
        await hub.unregister(websocket)
