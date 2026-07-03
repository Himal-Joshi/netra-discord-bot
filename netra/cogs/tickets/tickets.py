import discord
from discord import app_commands, ui
from discord.ext import commands
import logging
from typing import Optional

from netra.core.bot import Netra

log = logging.getLogger(__name__)

class TicketView(ui.View):
    def __init__(self, bot: Netra):
        super().__init__(timeout=None)
        self.bot = bot

    @ui.button(label="Open Support Ticket", style=discord.ButtonStyle.primary, custom_id="persistent:ticket_open")
    async def open_ticket(self, interaction: discord.Interaction, button: ui.Button):
        # Simplified ticket creation logic
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        channel = await interaction.guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            overwrites=overwrites,
            category=None # Should be configurable
        )

        await interaction.response.send_message(f"Ticket created: {channel.mention}", ephemeral=True)
        await channel.send(f"Welcome {interaction.user.mention}, support will be with you shortly.")

class Tickets(commands.Cog):
    def __init__(self, bot: Netra):
        self.bot = bot

    @app_commands.command(name="setup-tickets", description="Setup the ticket system in this channel")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup_tickets(self, interaction: discord.Interaction):
        view = TicketView(self.bot)
        await interaction.response.send_message("Click the button below to open a ticket.", view=view)

async def setup(bot: Netra):
    await bot.add_cog(Tickets(bot))
