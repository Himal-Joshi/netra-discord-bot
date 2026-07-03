import discord
from discord.ext import commands
import logging

log = logging.getLogger(__name__)

class Owner(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.is_owner()
    @commands.command(name="sync")
    async def sync(self, ctx: commands.Context):
        """Sync slash commands"""
        synced = await self.bot.tree.sync()
        await ctx.send(f"Synced {len(synced)} commands.")

async def setup(bot: commands.Bot):
    await bot.add_cog(Owner(bot))
