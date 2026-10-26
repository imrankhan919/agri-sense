import json
from typing import Any, Optional
import redis
from app.redis_client import r


def get_json(key: str) -> Optional[Any]:
    try:
        raw = r.get(key)
    except redis.RedisError:
        return None 
    return json.loads(raw) if raw else None


def set_json(key: str, value: Any, ttl_sec: int) -> None:
    try:
        r.set(key, json.dumps(value, default=str), ex=ttl_sec) 
    except redis.RedisError:
        pass

def delete(key: str) -> None:
    try:
        r.delete(key)
    except redis.RedisError:
        pass
