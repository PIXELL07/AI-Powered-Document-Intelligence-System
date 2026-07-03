"""
Why Redis pub/sub sits between Celery and the WebSocket:

The FastAPI process (holding the browser's WebSocket connection) and the
Celery worker process (running the CPU-bound pipeline stage) are different
OS processes -- possibly different machines on Railway. The worker can't
just "call a function" on the web process to push a stage update.

So: worker finishes a stage -> publishes a small JSON message to a Redis
channel named "doc:{document_id}" -> the web process (which subscribed to
that channel when the browser opened the WebSocket) receives it and
forwards it down the socket. This is the standard pattern for real-time
updates from background workers in a horizontally-scalable deployment.
"""
import asyncio
import json
import logging
from typing import Dict, Set

import redis.asyncio as aioredis
from fastapi import WebSocket

from app.config import settings

logger = logging.getLogger("websocket_manager")


class ConnectionManager:
    def __init__(self):
        # document_id -> set of active browser sockets watching it
        self._connections: Dict[str, Set[WebSocket]] = {}
        self._redis: aioredis.Redis | None = None
        self._pubsub = None
        self._listener_task: asyncio.Task | None = None

    async def startup(self):
        self._redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        self._pubsub = self._redis.pubsub()
        await self._pubsub.psubscribe("doc:*")
        self._listener_task = asyncio.create_task(self._listen())
        logger.info("WebSocket manager subscribed to Redis pattern doc:*")

    async def shutdown(self):
        if self._listener_task:
            self._listener_task.cancel()
        if self._pubsub:
            await self._pubsub.close()
        if self._redis:
            await self._redis.close()

    async def _listen(self):
        assert self._pubsub is not None
        async for message in self._pubsub.listen():
            if message["type"] != "pmessage":
                continue
            channel = message["channel"]  # "doc:{document_id}"
            document_id = channel.split(":", 1)[1]
            sockets = self._connections.get(document_id, set())
            if not sockets:
                continue
            dead = []
            for ws in sockets:
                try:
                    await ws.send_text(message["data"])
                except Exception:
                    dead.append(ws)
            for ws in dead:
                sockets.discard(ws)

    async def connect(self, document_id: str, websocket: WebSocket):
        await websocket.accept()
        self._connections.setdefault(document_id, set()).add(websocket)

    def disconnect(self, document_id: str, websocket: WebSocket):
        sockets = self._connections.get(document_id)
        if sockets:
            sockets.discard(websocket)
            if not sockets:
                self._connections.pop(document_id, None)


manager = ConnectionManager()


def publish_stage_update(document_id: str, payload: dict):
    """Synchronous publisher used from Celery worker processes (which are
    plain sync code, not asyncio). Uses a short-lived sync redis client."""
    import redis as sync_redis

    client = sync_redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        client.publish(f"doc:{document_id}", json.dumps(payload))
    finally:
        client.close()
