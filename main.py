import asyncio
import json
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Query, Path
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as aioredis
from hold_seat import hold_seat, confirm_seat, get_seats

import sentry_sdk
sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN"),
    send_default_pii=True,
)

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

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

async def redis_subscriber(redis: aioredis.Redis):
    """Single subscription per server process; fans out to local websockets."""
    pubsub = redis.pubsub()
    await pubsub.subscribe("seat_updates")
    async for message in pubsub.listen():
        if message["type"] == "message":
            await manager.broadcast(message["data"].decode())

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = aioredis.from_url(REDIS_URL)
    subscriber_task = asyncio.create_task(redis_subscriber(app.state.redis))
    yield
    subscriber_task.cancel()
    await app.state.redis.aclose()

app = FastAPI(lifespan=lifespan)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/seats")
async def seats():
    return get_seats()

@app.post("/seats/{seat_id}/hold")
@limiter.limit("10/minute")
async def hold(
    request: Request,
    seat_id: int = Path(..., ge=1, le=8),
    user_id: str = Query(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$"),
):
    won = hold_seat(seat_id, user_id)
    if won:
        await request.app.state.redis.publish(
            "seat_updates", json.dumps({"seat_id": seat_id, "status": "held", "user_id": user_id})
        )
    return {"held": won}

@app.post("/seats/{seat_id}/confirm")
@limiter.limit("10/minute")
async def confirm(
    request: Request,
    seat_id: int = Path(..., ge=1, le=8),
    user_id: str = Query(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$"),
    idempotency_key: str = Query(..., min_length=1, max_length=200),
):
    result = confirm_seat(seat_id, user_id, idempotency_key)
    if result["confirmed"] and not result["replay"]:
        await request.app.state.redis.publish(
            "seat_updates", json.dumps({"seat_id": seat_id, "status": "booked", "user_id": user_id})
        )
    return result

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # We never expect client messages; receiving is how we detect disconnects.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)
