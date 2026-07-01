from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from hold_seat import hold_seat
import redis.asyncio as aioredis
import json
import os

import sentry_sdk
sentry_sdk.init(
    dsn="https://18eafdc3d46c72e6147fa51ebe79bce1@o4511658894491648.ingest.us.sentry.io/4511658917691392",
    send_default_pii=True,
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost")

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                dead.append(connection)
        for connection in dead:
            self.active_connections.remove(connection)

manager = ConnectionManager()

@app.post("/seats/{seat_id}/hold")
async def hold(seat_id: int, user_id: str):
    won = hold_seat(seat_id, user_id)
    if won:
        r = aioredis.from_url(REDIS_URL)
        await r.publish("seat_updates", json.dumps({"seat_id": seat_id, "status": "held", "user_id": user_id}))
        await r.aclose()
    return {"held": won}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    r = aioredis.from_url(REDIS_URL)
    pubsub = r.pubsub()
    await pubsub.subscribe("seat_updates")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await manager.broadcast(message["data"].decode())
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    finally:
        manager.disconnect(websocket)
        await r.aclose()