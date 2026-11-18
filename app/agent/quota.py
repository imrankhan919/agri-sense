from datetime import date
import redis
from fastapi import HTTPException
from app.config import settings
from app.redis_client import r


def _key(user_id: int) -> str:
    return f"agent:tokens:{user_id}:{date.today().isoformat()}" # roz naya counter

def tokens_used_today(user_id: int) -> int:
    try:
        return int(r.get(_key(user_id)) or 0)
    except redis.RedisError:
        return 0

def check_quota(user_id: int) -> None:
    if tokens_used_today(user_id) >= settings.agent_daily_token_quota:
        raise HTTPException(429, "Aaj ka AI quota khatam ho gaya. Kal dobara try karo.")

def add_usage(user_id: int, tokens: int) -> None:
    try:
        pipe = r.pipeline()
        pipe.incrby(_key(user_id), tokens)
        pipe.expire(_key(user_id), 2 * 24 * 3600)
        pipe.execute()
    except redis.RedisError:
        pass