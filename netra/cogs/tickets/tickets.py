import discord
from discord import app_commands, ui
from discord.ext import commands
import logging
from typing import Optional, cast, Mapping, Union
import asyncio

from core.bot import Netra

log = logging.getLogger(__name__)

class TicketModal(ui.Modal, title='Open Support Ticket'):
    reason = ui.TextInput(
        label='Reason for opening ticket',
        style=discord.TextStyle.paragraph,
        placeholder='Please describe your issue in detail...',
        required=True,
        max_length=1000
    )

    def __init__(self, bot: Netra):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild or not isinstance(interaction.user, discord.Member):
            return

        from database.session import SessionLocal
        from models.systems import TicketSettings
        from sqlalchemy import select

        moderator_role_id = None
        async with SessionLocal() as session:
            result = await session.execute(select(TicketSettings).where(TicketSettings.guild_id == guild.id))
            settings = result.scalar_one_or_none()
            if settings and settings.moderator_role_id:
                moderator_role_id = settings.moderator_role_id

        overwrites = cast(
            Mapping[Union[discord.Member, discord.Object, discord.Role], discord.PermissionOverwrite],
            {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
        )

        channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            overwrites=overwrites,
            category=None, # Should be configurable
            topic=str(interaction.user.id)
        )

        await interaction.response.send_message(f"Ticket created: {channel.mention}", ephemeral=True)
        
        ping_text = f"<@&{moderator_role_id}> " if moderator_role_id else ""
        embed = discord.Embed(
            title="Ticket Opened",
            description=f"**Reason:**\n{self.reason.value}",
            color=discord.Color.blue()
        )
        await channel.send(f"Welcome {interaction.user.mention}! {ping_text}Support will be with you shortly.", embed=embed)

class TicketView(ui.View):
    def __init__(self, bot: Netra):
        super().__init__(timeout=None)
        self.bot = bot

    @ui.button(label="Open Support Ticket", style=discord.ButtonStyle.primary, custom_id="persistent:ticket_open")
    async def open_ticket(self, interaction: discord.Interaction, button: ui.Button):
        guild = interaction.guild
        if not guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("Tickets can only be opened in a server.", ephemeral=True)
            
        await interaction.response.send_modal(TicketModal(self.bot))

class Tickets(commands.Cog):
    def __init__(self, bot: Netra):
        self.bot = bot

    @app_commands.command(name="create-ticket", description="Create a new support ticket")
    async def create_ticket(self, interaction: discord.Interaction):
        view = TicketView(self.bot)
        await interaction.response.send_message("Click the button below to open a ticket.", view=view, ephemeral=True)

    @app_commands.command(name="close-ticket", description="Close the current ticket")
    async def close_ticket(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            
        if not isinstance(interaction.channel, discord.TextChannel) or not interaction.channel.name.startswith(("ticket-", "closed-")) or interaction.channel.name == "ticket-transcripts":
            return await interaction.response.send_message("This command can only be used inside a ticket channel.", ephemeral=True)

        from database.session import SessionLocal
        from models.systems import TicketSettings
        from sqlalchemy import select
        
        async with SessionLocal() as session:
            result = await session.execute(select(TicketSettings).where(TicketSettings.guild_id == guild.id))
            settings = result.scalar_one_or_none()
            
            is_admin = interaction.user.guild_permissions.manage_guild
            is_moderator = False
            
            if settings and settings.moderator_role_id:
                if any(role.id == settings.moderator_role_id for role in interaction.user.roles):
                    is_moderator = True

            if not (is_admin or is_moderator):
                return await interaction.response.send_message("Only an administrator or ticket moderator can close this ticket.", ephemeral=True)

            await interaction.response.send_message(f"🔒 **Ticket closed by {interaction.user.mention}. Generating transcript and deleting channel...**")
            
            # Generate transcript
            messages = [message async for message in interaction.channel.history(limit=200, oldest_first=True)]
            transcript = ""
            for msg in messages:
                timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
                transcript += f"[{timestamp}] {msg.author.name}: {msg.clean_content}\n"
                for attachment in msg.attachments:
                    transcript += f"[{timestamp}] {msg.author.name}: [Attachment: {attachment.url}]\n"
                    
            import io
            transcript_file = discord.File(io.BytesIO(transcript.encode('utf-8')), filename=f"transcript-{interaction.channel.name}.txt")
            
            transcript_channel = None
            if settings and settings.transcript_channel_id:
                transcript_channel = guild.get_channel(settings.transcript_channel_id)
                
            if not transcript_channel:
                overwrites = cast(
                    Mapping[Union[discord.Member, discord.Object, discord.Role], discord.PermissionOverwrite],
                    {
                        guild.default_role: discord.PermissionOverwrite(read_messages=False),
                        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                    }
                )
                transcript_channel = await guild.create_text_channel(
                    name="ticket-transcripts",
                    overwrites=overwrites
                )
                
                if not settings:
                    settings = TicketSettings(guild_id=guild.id)
                    session.add(settings)
                settings.transcript_channel_id = transcript_channel.id
                await session.commit()
                
        if transcript_channel and isinstance(transcript_channel, discord.TextChannel):
            await transcript_channel.send(f"Transcript for `{interaction.channel.name}` (Closed by {interaction.user.mention})", file=transcript_file)
            
        try:
            await interaction.channel.delete(reason=f"Ticket closed by {interaction.user.name}")
        except discord.NotFound:
            pass

    @app_commands.command(name="setup-tickets", description="Setup a persistent ticket panel in this channel")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup_tickets(self, interaction: discord.Interaction):
        view = TicketView(self.bot)
        if interaction.channel and isinstance(interaction.channel, discord.TextChannel):
            await interaction.channel.send("Click the button below to open a ticket.", view=view)
            await interaction.response.send_message("Ticket panel successfully created!", ephemeral=True)
        else:
            await interaction.response.send_message("This command must be used in a text channel.", ephemeral=True)

    @app_commands.command(name="setticket-moderator", description="Set the role that is pinged when a ticket is opened")
    @app_commands.default_permissions(manage_guild=True)
    async def setticket_moderator(self, interaction: discord.Interaction, role: discord.Role):
        guild = interaction.guild
        if not guild:
            return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            
        from database.session import SessionLocal
        from models.systems import TicketSettings
        from sqlalchemy import select
        
        async with SessionLocal() as session:
            result = await session.execute(select(TicketSettings).where(TicketSettings.guild_id == guild.id))
            settings = result.scalar_one_or_none()
            if not settings:
                settings = TicketSettings(guild_id=guild.id)
                session.add(settings)
            
            settings.moderator_role_id = role.id
            await session.commit()
            
        await interaction.response.send_message(f"Ticket moderator role successfully set to {role.mention}", ephemeral=True)

async def setup(bot: Netra):
    await bot.add_cog(Tickets(bot))
