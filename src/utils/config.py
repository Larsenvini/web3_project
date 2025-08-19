import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    DATABASE_URL: str

    REDIS_URL: str
    PROJECT_NAME: str = "DeFi Backend MVP"
    API_V1_STR: str = "/api/v1"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()