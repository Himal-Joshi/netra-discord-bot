import discord
from discord import app_commands
from discord.ext import commands
import logging
from datetime import datetime
from typing import Optional
import dateparser
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from netra.core.bot import Netra
from netra.core.config import settings
from netra.models.reminder import Reminder
from sqlalchemy import select

log = logging.getLogger(__name__)

class Reminders(commands.Cog):
    def __init__(self, bot: Netra):
        self.bot = bot
        # In production, use the database URL for APScheduler persistence
        job_stores = {
            'default': SQLAlchemyJobStore(url=settings.DATABASE_URL.replace("aiosqlite", "sqlite"))
        }
        self.scheduler = AsyncIOScheduler(jobstores=job_stores)
        self.scheduler.start()

    async def send_reminder(self, user_id: int, channel_id: int, content: str):
        channel = self.bot.get_channel(channel_id)
        if not channel:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except discord.HTTPException:
                return

        await channel.send(f"🔔 <@{user_id}>: {content}")

    @app_commands.command(name="remind", description="Set a reminder")
    async def remind(self, interaction: discord.Interaction, time_str: str, message: str):
        now = datetime.now()
        due_date = dateparser.parse(time_str, settings={'RELATIVE_BASE': now, 'PREFER_DATES_FROM': 'future'})

        if not due_date or due_date < now:
            return await interaction.response.send_message("Invalid time format or time is in the past.", ephemeral=True)

        # Store in DB and Schedule
        self.scheduler.add_job(
            self.send_reminder,
            'date',
            run_date=due_date,
            args=[interaction.user.id, interaction.channel_id, message]
        )

        await interaction.response.send_message(f"OK! I'll remind you at {due_date.strftime('%Y-%m-%d %H:%M:%S')} about: {message}")

async def setup(bot: Netra):
    await bot.add_cog(Reminders(bot))
