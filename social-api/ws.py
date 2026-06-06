"""WebSocket watch-party sync + reactions for social-service."""
import asyncio
import json
from datetime import datetime, timezone
from fastapi import WebSocket, WebSocketDisconnect

PARTY_ROOMS: dict[str, set[WebSocket]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def broadcast(room_id: str, msg: dict):
    payload = json.dumps({**msg, "at": _now()})
    snapshot = list(PARTY_ROOMS.get(room_id, set()))
    await asyncio.gather(*[ws.send_text(payload) for ws in snapshot],
                          return_exceptions=True)


def register_ws_routes(app):
    @app.websocket("/party/{room_id}")
    async def party_ws(websocket: WebSocket, room_id: str):
        await websocket.accept()
        room = PARTY_ROOMS.setdefault(room_id, set())
        room.add(websocket)
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    msg = json.loads(data)
                except json.JSONDecodeError:
                    msg = {"type": "chat", "text": data}
                if isinstance(msg.get("text"), str) and len(msg["text"]) > 500:
                    msg["text"] = msg["text"][:500] + "…"
                await broadcast(room_id, msg)
        except WebSocketDisconnect:
            room.discard(websocket)
