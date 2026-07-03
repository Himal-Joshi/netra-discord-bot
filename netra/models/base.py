from datetime import datetime, timezone
from sqlalchemy import BigInteger, Column, DateTime, String, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

from typing import Optional

class GuildConfig(Base):
    __tablename__ = "guild_configs"

    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    prefix: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    language: Mapped[str] = mapped_column(String(5), default="en")

    # Feature Toggles
    mod_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    music_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    tickets_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
