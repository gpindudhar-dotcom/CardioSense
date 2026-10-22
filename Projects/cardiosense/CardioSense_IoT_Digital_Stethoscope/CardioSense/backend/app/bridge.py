"""
Outbound bridge: backend connects to ESP32 WebSocket server and relays binary packets.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from .websocket import hub

logger = logging.getLogger("cardiosense.bridge")


class DeviceBridge:
    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._url: Optional[str] = None
        self._stop = asyncio.Event()

    @property
    def active(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def url(self) -> Optional[str]:
        return self._url

    async def start(self, host: str, port: int = 81, path: str = "/") -> str:
        host = host.strip()
        if not host:
            raise ValueError("ESP32 host/IP is required.")
        url = f"ws://{host}:{port}{path}"
        await self.stop()
        self._url = url
        self._stop = asyncio.Event()
        self._task = asyncio.create_task(self._run(url, host))
        return url

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._stop.set()
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None

    async def _run(self, url: str, host: str) -> None:
        import websockets

        hub.state.ip = host
        backoff = 1.0
        while not self._stop.is_set():
            try:
                logger.info("Connecting to ESP32 at %s", url)
                async with websockets.connect(url, max_size=2_000_000, open_timeout=5) as ws:
                    hub.state.connected = True
                    hub.state.wifi_connected = True
                    hub.state.ip = host
                    backoff = 1.0
                    await hub.broadcast({"type": "device_status", "data": hub.state.to_dict()})
                    await ws.send("status")
                    while not self._stop.is_set():
                        try:
                            message = await asyncio.wait_for(ws.recv(), timeout=5.0)
                        except asyncio.TimeoutError:
                            try:
                                await ws.send("ping")
                            except Exception:
                                break
                            continue
                        if isinstance(message, bytes):
                            await hub.handle_device_packet(message)
                        elif isinstance(message, str):
                            try:
                                import json

                                data = json.loads(message)
                            except json.JSONDecodeError:
                                logger.warning("Ignoring non-JSON text frame from ESP32 at %s", host)
                                continue
                            if not isinstance(data, dict):
                                logger.warning("Ignoring non-object JSON frame from ESP32 at %s", host)
                            elif data.get("type") == "status":
                                try:
                                    hub.state.device_id = data.get("device_id", hub.state.device_id)
                                    hub.state.rssi = data.get("rssi", hub.state.rssi)
                                    hub.state.sample_rate = int(data.get("sample_rate", hub.state.sample_rate))
                                    hub.state.wifi_connected = bool(data.get("wifi_connected", True))
                                    await hub.broadcast({"type": "device_status", "data": hub.state.to_dict()})
                                except (TypeError, ValueError, OverflowError):
                                    logger.exception("Invalid ESP32 status frame from %s", host)
                            elif hub.legacy_sample(data):
                                await hub.handle_legacy_sample(data)
                            else:
                                logger.warning("Ignoring unsupported JSON frame from ESP32 at %s", host)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning("ESP32 bridge error: %s", exc)
                hub.state.connected = False
                await hub.broadcast(
                    {
                        "type": "error",
                        "message": f"ESP32 bridge disconnected ({exc}). Retrying…",
                    }
                )
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=backoff)
                except asyncio.TimeoutError:
                    pass
                backoff = min(8.0, backoff * 1.5)
        hub.state.connected = False


bridge = DeviceBridge()
