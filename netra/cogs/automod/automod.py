import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Optional
import re

from core.bot import Netra

log = logging.getLogger(__name__)

class AutoMod(commands.Cog):
    def __init__(self, bot: Netra):
        self.bot = bot
        # Invite regex
        self.invite_regex = re.compile(r"(discord\.gg/|discord\.com/invite/|discordapp\.com/invite/)([a-zA-Z0-9]+)")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # Fetch blacklisted words for this guild
        blacklisted = []
        try:
            from database.session import SessionLocal
            from models.systems import AutoModSettings
            from sqlalchemy.future import select
            
            async with SessionLocal() as session:
                result = await session.execute(select(AutoModSettings).where(AutoModSettings.guild_id == message.guild.id))
                settings = result.scalar_one_or_none()
                if settings and settings.blacklisted_words:
                    blacklisted = settings.blacklisted_words
        except Exception as e:
            log.error(f"Failed to fetch automod settings: {e}")

        content_lower = message.content.lower()
        
        # Check blacklisted words
        for word in blacklisted:
            if word.lower() in content_lower:
                if not message.author.guild_permissions.manage_messages:
                    try:
                        await message.delete()
                        await message.channel.send(f"{message.author.mention}, watch your language! That word is blacklisted.", delete_after=5)
                        return # Stop processing
                    except discord.Forbidden:
                        pass

        # Simple invite protection
        if self.invite_regex.search(message.content):
            # Check for whitelist or permissions (simplified for now)
            if not message.author.guild_permissions.manage_messages:
                try:
                    await message.delete()
                    await message.channel.send(f"{message.author.mention}, invite links are not allowed here!", delete_after=5)
                except discord.Forbidden:
                    pass

async def setup(bot: Netra):
    await bot.add_cog(AutoMod(bot))
