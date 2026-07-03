import discord
from discord import app_commands
from discord.ext import commands
import time
from typing import Optional

from core.bot import Netra
from core.i18n import i18n

class Utility(commands.Cog):
    def __init__(self, bot: Netra):
        self.bot = bot

    @app_commands.command(name="ping", description="Check the bot's latency")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        # Assuming we have a guild or default to 'en'
        locale = "en"
        response = i18n.get(locale, "ping-response", latency=latency)
        await interaction.response.send_message(response)

    @app_commands.command(name="serverinfo", description="Get information about the server")
    @app_commands.guild_only()
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        embed = discord.Embed(title=f"Server Info: {guild.name}", color=discord.Color.blue())
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Unknown")
        embed.add_field(name="Members", value=str(guild.member_count))
        embed.add_field(name="Roles", value=str(len(guild.roles)))
        embed.add_field(name="Channels", value=str(len(guild.channels)))
        embed.set_footer(text=f"ID: {guild.id} | Created at: {guild.created_at.strftime('%Y-%m-%d')}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="userinfo", description="Get information about a user")
    async def userinfo(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        member = member or interaction.user
        embed = discord.Embed(title=f"User Info: {member.name}", color=member.color)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="ID", value=str(member.id))
        embed.add_field(name="Joined At", value=member.joined_at.strftime('%Y-%m-%d') if member.joined_at else "N/A")
        embed.add_field(name="Roles", value=", ".join([role.mention for role in member.roles[1:10]]) + ("..." if len(member.roles) > 10 else ""))
        await interaction.response.send_message(embed=embed)

async def setup(bot: Netra):
    await bot.add_cog(Utility(bot))
