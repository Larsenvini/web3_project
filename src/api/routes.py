from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.db.database import get_db
from src.db import models

router = APIRouter()

@router.get("/ping")
async def ping():
    return {"message": "pong"}

@router.get("/blocks")
async def get_blocks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.BlockHeader).order_by(models.BlockHeader.id.desc()).limit(10))
    blocks = result.scalars().all()
    return [{"id": b.id, "block_number": b.block_number, "timestamp": b.timestamp} for b in blocks]