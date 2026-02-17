import asyncio
from typing import Any

from fastapi import WebSocket


class RealtimeHub:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(websocket)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        async with self._lock:
            clients = list(self._clients)
        disconnected: list[WebSocket] = []
        for client in clients:
            try:
                await client.send_json(payload)
            except Exception:
                disconnected.append(client)
        if disconnected:
            async with self._lock:
                for client in disconnected:
                    self._clients.discard(client)

    async def size(self) -> int:
        async with self._lock:
            return len(self._clients)


realtime_hub = RealtimeHub()
