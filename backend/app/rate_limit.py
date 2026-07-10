"""
Fixed-window rate limiting for auth endpoints, backed by Redis rather than
an in-process dict.

Why Redis and not a simple in-memory counter: in production this app runs
as multiple uvicorn worker processes (see Procfile / README "Scaling to
concurrent users"), each an independent Python process with its own
memory. An in-memory counter would only see the requests that happened to
land on that one process, making the real limit effectively
(configured_limit x number_of_processes) -- Redis gives one shared count
all processes agree on.

Applied to /api/auth/login and /api/auth/signup, since those are the
routes most worth protecting against brute-force/abuse (unauthenticated,
directly gate account access).
"""
import time
from fastapi import HTTPException, Request
import redis as sync_redis

from app.config import settings

_pool = None


def _client():
    global _pool
    if _pool is None:
        _pool = sync_redis.ConnectionPool.from_url(
            settings.REDIS_URL, decode_responses=True, max_connections=20
        )
    return sync_redis.Redis(connection_pool=_pool)


def enforce_rate_limit(key: str, limit: int, window_seconds: int):
    """Raises 429 if `key` has been hit more than `limit` times in the
    current fixed window. A fixed window (vs. sliding/token-bucket) is a
    deliberate simplicity tradeoff -- it allows a short burst right at a
    window boundary, but that's an acceptable tradeoff for login abuse
    protection and avoids needing a Lua script for atomicity."""
    client = _client()
    window = int(time.time() // window_seconds)
    redis_key = f"ratelimit:{key}:{window}"
    try:
        count = client.incr(redis_key)
        if count == 1:
            client.expire(redis_key, window_seconds)
    except sync_redis.exceptions.RedisError:
        # If Redis itself is unreachable, fail OPEN (allow the request)
        # rather than taking down auth entirely because of a rate-limiter
        # outage -- availability of login matters more than perfect abuse
        # protection during a Redis blip.
        return
    if count > limit:
        raise HTTPException(429, "Too many attempts. Please wait a moment and try again.")


def rate_limit_by_ip(request: Request, action: str, limit: int = 10, window_seconds: int = 60):
    client_ip = request.client.host if request.client else "unknown"
    enforce_rate_limit(f"{action}:{client_ip}", limit, window_seconds)
