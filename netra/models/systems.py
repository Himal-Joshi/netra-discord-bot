from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import BigInteger, String, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base

class Notice(Base):
    __tablename__ = "notices"

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(String(2000))
    template_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    category: Mapped[str] = mapped_column(String(50)) # support, appeal, etc.
    status: Mapped[str] = mapped_column(String(20), default="open") # open, closed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

class TicketSettings(Base):
    __tablename__ = "ticket_settings"

    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    moderator_role_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    transcript_channel_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

class AutoModSettings(Base):
    __tablename__ = "automod_settings"
    
    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    blacklisted_words: Mapped[list] = mapped_column(JSON, default=list)
    warning_message: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)

class WelcomeSettings(Base):
    __tablename__ = "welcome_settings"
    
    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    channel_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    message: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
