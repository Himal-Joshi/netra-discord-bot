import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Optional
import re

from netra.core.bot import Netra

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
