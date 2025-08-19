import asyncio
from fastapi import FastAPI
from src.utils.config import settings
from src.utils.logger import setup_logging
from src.api import routes
from src.blockchain.listener import listen_blocks

setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.include_router(routes.router, prefix=settings.API_V1_STR)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(listen_blocks())

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}