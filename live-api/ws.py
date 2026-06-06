"""WebSocket chat for live-service. Mounted by main.py."""
import asyncio
import json
from datetime import datetime, timezone
from fastapi import WebSocket, WebSocketDisconnect

ROOMS: dict[str, set[WebSocket]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def register_ws_routes(app):
    @app.websocket("/live/{stream_id}/chat")
    async def chat_ws(websocket: WebSocket, stream_id: str):
        await websocket.accept()
        room = ROOMS.setdefault(stream_id, set())
        room.add(websocket)
        try:
            await websocket.send_json({
                "type": "system",
                "text": f"Welcome to {stream_id}. {len(room)} connected.",
                "at": _now(),
            })
            while True:
                data = await websocket.receive_text()
                try:
                    msg = json.loads(data)
                except json.JSONDecodeError:
                    msg = {"type": "chat", "text": data}
                # Defensive: drop oversize messages
                if isinstance(msg.get("text"), str) and len(msg["text"]) > 500:
                    msg["text"] = msg["text"][:500] + "…"
                payload = json.dumps({**msg, "at": _now()})
                # Snapshot to avoid set-mutated-during-iteration on disconnects
                snapshot = list(room)
                await asyncio.gather(
                    *[ws.send_text(payload) for ws in snapshot],
                    return_exceptions=True,
                )
        except WebSocketDisconnect:
            room.discard(websocket)
