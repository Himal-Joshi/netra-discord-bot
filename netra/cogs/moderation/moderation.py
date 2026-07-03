import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Optional
from datetime import timedelta

from netra.core.bot import Netra
from netra.models.moderation import Warning, ModLog
from sqlalchemy import select

log = logging.getLogger(__name__)

class Moderation(commands.Cog):
    def __init__(self, bot: Netra):
        self.bot = bot

    @app_commands.command(name="kick", description="Kick a member from the server")
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.checks.bot_has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = None):
        if member.top_role >= interaction.user.top_role:
            return await interaction.response.send_message("You cannot kick this member due to role hierarchy.", ephemeral=True)

        if member.top_role >= interaction.guild.me.top_role:
            return await interaction.response.send_message("I cannot kick this member due to role hierarchy.", ephemeral=True)

        try:
            await member.kick(reason=reason)
            await interaction.response.send_message(f"Successfully kicked {member.mention} for: {reason or 'No reason provided'}")
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to kick this member.", ephemeral=True)
        except discord.HTTPException:
            await interaction.response.send_message("Kicking failed due to an error.", ephemeral=True)

    @app_commands.command(name="ban", description="Ban a member from the server")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = None, delete_messages_days: int = 0):
        if member.top_role >= interaction.user.top_role:
            return await interaction.response.send_message("You cannot ban this member due to role hierarchy.", ephemeral=True)

        await member.ban(reason=reason, delete_message_days=delete_messages_days)
        await interaction.response.send_message(f"Successfully banned {member.mention} for: {reason or 'No reason provided'}")

    @app_commands.command(name="timeout", description="Timeout a member")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, minutes: int, reason: Optional[str] = None):
        if member.top_role >= interaction.user.top_role:
            return await interaction.response.send_message("You cannot timeout this member due to role hierarchy.", ephemeral=True)

        duration = timedelta(minutes=minutes)
        await member.timeout(duration, reason=reason)
        await interaction.response.send_message(f"Timed out {member.mention} for {minutes} minutes. Reason: {reason or 'No reason provided'}")

async def setup(bot: Netra):
    await bot.add_cog(Moderation(bot))
