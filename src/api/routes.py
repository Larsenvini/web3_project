from fastapi import APIRouter, Depends, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.db.database import get_db
from src.db import models
from src.utils.redis_client import get_redis
import asyncio

router = APIRouter()

@router.get("/ping")
async def ping():
    return {"message": "pong"}

@router.get("/blocks")
async def get_blocks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.BlockHeader).order_by(models.BlockHeader.id.desc()).limit(10))
    blocks = result.scalars().all()
    return [{"id": b.id, "block_number": b.block_number, "timestamp": b.timestamp} for b in blocks]

@router.websocket("/ws/blocks")
async def ws_blocks(websocket: WebSocket):
    await websocket.accept()
    redis = await get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe("blocks")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])
    finally:
        await pubsub.unsubscribe("blocks")
        await websocket.close()