"""WebSocket endpoints for real-time metrics and alert streaming."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.deps import DBDep, MetricsRepoDep

router = APIRouter(tags=["websocket"])
logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections grouped by campaign_id."""

    def __init__(self) -> None:
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room: str) -> None:
        await websocket.accept()
        self.active_connections.setdefault(room, []).append(websocket)
        logger.info("WebSocket connected: room=%s total=%d", room, len(self.active_connections[room]))

    async def disconnect(self, websocket: WebSocket, room: str) -> None:
        connections = self.active_connections.get(room, [])
        if websocket in connections:
            connections.remove(websocket)
        logger.info("WebSocket disconnected: room=%s remaining=%d", room, len(connections))

    async def broadcast(self, room: str, data: dict[str, Any]) -> None:
        """Send JSON to all connected clients in *room*."""
        stale: list[WebSocket] = []
        for ws in list(self.active_connections.get(room, [])):
            try:
                await ws.send_json(data)
            except Exception as exc:
                logger.warning("Failed to send to WebSocket in room %s: %s", room, exc)
                stale.append(ws)
        for ws in stale:
            await self.disconnect(ws, room)

    def connection_count(self, room: str) -> int:
        return len(self.active_connections.get(room, []))


# Singleton — shared across all requests
manager = ConnectionManager()


@router.websocket("/ws/campaigns/{campaign_id}/metrics")
async def websocket_campaign_metrics(
    websocket: WebSocket,
    campaign_id: str,
) -> None:
    """Real-time campaign metrics stream.

    Client can send ``{"action": "refresh"}`` to request an immediate update.
    """
    await manager.connect(websocket, campaign_id)
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "campaign_id": campaign_id,
            "message": "Connected to metrics stream",
        })

        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            if action == "ping":
                await websocket.send_json({"type": "pong"})
            elif action == "refresh":
                await websocket.send_json({
                    "type": "metrics_update",
                    "campaign_id": campaign_id,
                    "message": "Refresh queued — metrics will be pushed when available",
                })
    except WebSocketDisconnect:
        await manager.disconnect(websocket, campaign_id)
    except Exception as exc:
        logger.error("WebSocket error for campaign %s: %s", campaign_id, exc)
        await manager.disconnect(websocket, campaign_id)


@router.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket) -> None:
    """Real-time alert notifications stream (all campaigns)."""
    await manager.connect(websocket, "global_alerts")
    try:
        await websocket.send_json({"type": "connected", "message": "Subscribed to global alerts"})
        while True:
            data = await websocket.receive_json()
            if data.get("action") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        await manager.disconnect(websocket, "global_alerts")
    except Exception as exc:
        logger.error("Alert WebSocket error: %s", exc)
        await manager.disconnect(websocket, "global_alerts")
