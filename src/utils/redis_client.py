import aioredis

# single connection pool to be reused
redis = None

async def get_redis():
    global redis
    if redis is None:
        redis = await aioredis.from_url("redis://localhost", decode_responses=True)
    return redis
