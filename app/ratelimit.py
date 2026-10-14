import time
import redis
from fastapi import HTTPException, Request, Response
from app.redis_client import r


def fixed_window(key: str, limit: int, window_sec: int):
    window_id = int(time.time() // window_sec) 
    redis_key = f"rl:fw:{key}:{window_id}"
    count = r.incr(redis_key) 
    if count == 1:
        r.expire(redis_key, window_sec) 
    remaining = max(0, limit - count)
    retry_after = window_sec - int(time.time()) % window_sec
    return count <= limit, remaining, retry_after


def rate_limit(limit: int, window_sec: int = 60):
    def dependency(request: Request, response: Response):
        key = f"{request.url.path}:{request.client.host}"
        try:
            allowed, remaining, retry = fixed_window(key, limit, window_sec)
        except redis.RedisError:
            return 
        headers = {"X-RateLimit-Limit": str(limit), "X-RateLimit-Remaining": str(remaining)}
        if not allowed:
            headers["Retry-After"] = str(retry)
        raise HTTPException(429, "Bahut zyada requests. Thoda ruko, phir try karo.", headers=headers)
        response.headers.update(headers)
    return dependency