import discord
from discord import app_commands
from discord.ext import commands
import logging
from datetime import datetime
from typing import Optional
import dateparser
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from core.bot import Netra
from core.config import settings
from models.reminder import Reminder
from sqlalchemy import select

log = logging.getLogger(__name__)

# Global reference to bot for the apscheduler job
_bot_instance = None

async def execute_reminder(user_id: int, channel_id: int, content: str):
    if not _bot_instance:
        return
        
    channel = _bot_instance.get_channel(channel_id)
    if not channel:
        try:
            channel = await _bot_instance.fetch_channel(channel_id)
        except discord.HTTPException:
            return

    if isinstance(channel, (discord.TextChannel, discord.VoiceChannel, discord.Thread)):
        await channel.send(f"🔔 <@{user_id}>: {content}")

async def execute_announcement(channel_id: int, message: str, role_id: Optional[int], ping_everyone: bool):
    if not _bot_instance:
        return
        
    channel = _bot_instance.get_channel(channel_id)
    if not channel:
        try:
            channel = await _bot_instance.fetch_channel(channel_id)
        except discord.HTTPException:
            return

    if isinstance(channel, (discord.TextChannel, discord.VoiceChannel, discord.Thread)):
        ping_text = ""
        if ping_everyone:
            ping_text = "@everyone "
        elif role_id:
            ping_text = f"<@&{role_id}> "
            
        full_message = f"{ping_text}\n{message}" if ping_text else message
        await channel.send(full_message)

class Reminders(commands.Cog):
    def __init__(self, bot: Netra):
        self.bot = bot
        global _bot_instance
        _bot_instance = bot
        
        # In production, use the database URL for APScheduler persistence
        jobstores = {
            'default': SQLAlchemyJobStore(url=settings.DATABASE_URL.replace("+aiosqlite", ""))
        }
        self.scheduler = AsyncIOScheduler(jobstores=jobstores)
        self.scheduler.start()

    @app_commands.command(name="announce", description="Schedule an announcement in a specific channel")
    @app_commands.describe(
        time_str="When? (e.g., '10m', 'tomorrow at 5pm')",
        channel="The channel to send the announcement in",
        message="The message to announce",
        role_to_ping="Specific role to ping (Optional)",
        ping_everyone="Ping @everyone? (Overrides role_to_ping)"
    )
    @app_commands.default_permissions(administrator=True)
    async def announce(
        self, 
        interaction: discord.Interaction, 
        time_str: str, 
        channel: discord.TextChannel, 
        message: str, 
        role_to_ping: Optional[discord.Role] = None, 
        ping_everyone: Optional[bool] = False
    ):
        await interaction.response.defer(ephemeral=True)
        
        now = datetime.now()
        due_date = dateparser.parse(time_str, settings={'RELATIVE_BASE': now, 'PREFER_DATES_FROM': 'future'})

        if not due_date or due_date < now:
            return await interaction.followup.send("Invalid time format or time is in the past.")

        role_id = role_to_ping.id if role_to_ping else None

        self.scheduler.add_job(
            execute_announcement,
            'date',
            run_date=due_date,
            args=[channel.id, message, role_id, ping_everyone]
        )

        await interaction.followup.send(f"📢 Announcement scheduled in {channel.mention} at {due_date.strftime('%Y-%m-%d %H:%M:%S')}!")

    @app_commands.command(name="remind", description="Set a reminder")
    @app_commands.describe(
        time_str="When? (e.g., '10m' for 10 minutes, '2h', 'tomorrow', 'in 3 days')",
        message="What should I remind you about?"
    )
    async def remind(self, interaction: discord.Interaction, time_str: str, message: str):
        # deferring the response gives us up to 15 minutes to reply!
        # ephemeral=True hides the confirmation message from other users
        await interaction.response.defer(ephemeral=True)
        
        now = datetime.now()
        due_date = dateparser.parse(time_str, settings={'RELATIVE_BASE': now, 'PREFER_DATES_FROM': 'future'})

        if not due_date or due_date < now:
            return await interaction.followup.send("Invalid time format or time is in the past.")

        # Store in DB and Schedule
        self.scheduler.add_job(
            execute_reminder,
            'date',
            run_date=due_date,
            args=[interaction.user.id, interaction.channel_id, message]
        )

        await interaction.followup.send(f"OK! I'll remind you at {due_date.strftime('%Y-%m-%d %H:%M:%S')} about: {message}")

async def setup(bot: Netra):
    await bot.add_cog(Reminders(bot))
