from datetime import datetime
from sqlalchemy import BigInteger, String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from models.base import Base

class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    channel_id: Mapped[int] = mapped_column(BigInteger)
    guild_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    content: Mapped[str] = mapped_column(String(1000))
    due_date: Mapped[datetime] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    recurrence_interval: Mapped[str] = mapped_column(String(50), nullable=True) # daily, weekly, etc.
