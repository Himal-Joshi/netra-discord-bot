import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Discord
    DISCORD_TOKEN: str
    DISCORD_CLIENT_ID: str
    DISCORD_CLIENT_SECRET: str

    # Bot
    BOT_PREFIX: str = "n!"
    OWNER_IDS: List[int] = Field(default_factory=list)
    DEFAULT_GUILD_ID: Optional[int] = None

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///data/netra.db"

    # Logging
    LOG_LEVEL: str = "INFO"

    # Sentry
    SENTRY_DSN: Optional[str] = None

    # Music
    MUSIC_MAX_QUEUE_SIZE: int = 100
    MUSIC_DEFAULT_VOLUME: int = 50

    # Dashboard
    DASHBOARD_HOST: str = "0.0.0.0"
    DASHBOARD_PORT: int = 8000
    SECRET_KEY: str = "dev_secret_key"

    # Lavalink
    LAVALINK_HOST: str = "127.0.0.1"
    LAVALINK_PORT: int = 2333
    LAVALINK_PASSWORD: str = "youshallnotpass"

    @field_validator("OWNER_IDS", mode="before")
    @classmethod
    def parse_owner_ids(cls, v):
        if isinstance(v, str):
            return [int(i.strip()) for i in v.split(",") if i.strip()]
        if isinstance(v, int):
            return [v]
        return v

    @field_validator("DEFAULT_GUILD_ID", mode="before")
    @classmethod
    def parse_guild_id(cls, v):
        if isinstance(v, str) and not v.strip():
            return None
        return v

settings = Settings()
