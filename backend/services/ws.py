"""Minimal WebSocket connection manager, keyed by batch id."""
from __future__ import annotations

from fastapi import WebSocket


class WSManager:
    def __init__(self) -> None:
        self._conns: dict[int, set[WebSocket]] = {}

    async def connect(self, batch_id: int, ws: WebSocket) -> None:
        await ws.accept()
        self._conns.setdefault(batch_id, set()).add(ws)

    def disconnect(self, batch_id: int, ws: WebSocket) -> None:
        conns = self._conns.get(batch_id)
        if conns:
            conns.discard(ws)
            if not conns:
                self._conns.pop(batch_id, None)

    async def broadcast(self, batch_id: int, message: dict) -> None:
        for ws in list(self._conns.get(batch_id, set())):
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(batch_id, ws)


manager = WSManager()
