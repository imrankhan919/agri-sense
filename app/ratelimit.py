import time
import jwt
import redis
import uuid
from fastapi import HTTPException, Request, Response
from app.redis_client import r
from app.security import decode_token


def get_identity(request: Request) -> str:
   auth = request.headers.get("authorization", "")
   if auth.lower().startswith("bearer "):
           try:
               return f"user:{decode_token(auth[7:])['sub']}"
           except jwt.PyJWTError:
               pass
   return f"ip:{request.client.host}"


def fixed_window(key: str, limit: int, window_sec: int):
    window_id = int(time.time() // window_sec) 
    redis_key = f"rl:fw:{key}:{window_id}"
    count = r.incr(redis_key) 
    if count == 1:
        r.expire(redis_key, window_sec) 
    remaining = max(0, limit - count)
    retry_after = window_sec - int(time.time()) % window_sec
    return count <= limit, remaining, retry_after


def sliding_window(key: str, limit: int, window_sec: int):
    now = time.time()
    redis_key = f"rl:sw:{key}"
    pipe = r.pipeline()
    pipe.zremrangebyscore(redis_key, 0, now - window_sec) # purane hits hatao
    pipe.zcard(redis_key) # abhi kitne bache
    _, count = pipe.execute()
    if count >= limit:
        oldest = r.zrange(redis_key, 0, 0, withscores=True)
        retry = int(oldest[0][1] + window_sec - now) + 1 if oldest else window_sec
        return False, 0, retry
    pipe = r.pipeline()
    pipe.zadd(redis_key, {f"{now}-{uuid.uuid4().hex[:6]}": now})
    pipe.expire(redis_key, window_sec)
    pipe.execute()
    return True, limit - count - 1, 0


TOKEN_BUCKET_LUA = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill = tonumber(ARGV[2]) -- tokens per second
local now = tonumber(ARGV[3])
local data = redis.call('HMGET', key, 'tokens', 'ts')
local tokens = tonumber(data[1])
local ts = tonumber(data[2])
if tokens == nil then tokens = capacity; ts = now end
tokens = math.min(capacity, tokens + math.max(0, now - ts) * refill)
local allowed = 0
if tokens >= 1 then tokens = tokens - 1; allowed = 1 end
redis.call('HSET', key, 'tokens', tokens, 'ts', now)
redis.call('EXPIRE', key, math.ceil(capacity / refill) * 2)
return {allowed, tostring(tokens)}
"""
_bucket_script = r.register_script(TOKEN_BUCKET_LUA)


def token_bucket(key: str, capacity: int, refill_per_sec: float):
   allowed, tokens = _bucket_script(keys=[f"rl:tb:{key}"], args=[capacity, refill_per_sec, time.time()])
   tokens = float(tokens)
   retry = 0 if allowed else int((1 - tokens) / refill_per_sec) + 1
   return bool(allowed), int(tokens), retry




def rate_limit(limit: int, window_sec: int = 60 , algo: str = "fixed"):
    def dependency(request: Request, response: Response):
        key = f"{request.url.path}:{get_identity(request)}"
        try:
            if algo == "fixed":
                allowed, remaining, retry = fixed_window(key, limit, window_sec)
            elif algo == "sliding":
                allowed, remaining, retry = sliding_window(key, limit, window_sec)
            else:
                allowed, remaining, retry = token_bucket(key, limit, limit / window_sec)
        except redis.RedisError:
            return # fail-open
        headers = {"X-RateLimit-Limit": str(limit), "X-RateLimit-Remaining": str(remaining)}
        if not allowed:
            headers["Retry-After"] = str(retry)
            raise HTTPException(429, "Bahut zyada requests. Thoda ruko, phir try karo.", headers=headers)
        response.headers.update(headers)
    return dependency