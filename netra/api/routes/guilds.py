from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import Optional

from database.session import SessionLocal
from models.systems import TicketSettings, AutoModSettings, WelcomeSettings
from api.dependencies import verify_guild_admin
import api.server
import discord

router = APIRouter()

class TicketSettingsUpdate(BaseModel):
    transcript_channel_id: Optional[int] = None
    moderator_role_id: Optional[int] = None

class AutoModSettingsUpdate(BaseModel):
    blacklisted_words: list[str]

class WelcomeSettingsUpdate(BaseModel):
    channel_id: Optional[int] = None
    message: Optional[str] = None
    image_url: Optional[str] = None

class EmbedSendRequest(BaseModel):
    channel_id: int
    title: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    image_url: Optional[str] = None

@router.get("/bot-guilds")
async def get_bot_guilds():
    """
    Returns a list of guild IDs the bot is currently in as strings.
    """
    bot = api.server.bot_instance
    if not bot:
        return []
    return [str(guild.id) for guild in bot.guilds]

@router.get("/{guild_id}/ticket-settings")
async def get_ticket_settings(guild_id: int, is_admin: bool = Depends(verify_guild_admin)):
    """
    Fetches the ticket settings for a specific guild.
    Requires a valid Discord access token with Admin/Manage Guild permissions for this guild.
    """
    async with SessionLocal() as session:
        result = await session.execute(select(TicketSettings).where(TicketSettings.guild_id == guild_id))
        settings = result.scalar_one_or_none()
        
        if not settings:
            return {
                "guild_id": guild_id,
                "transcript_channel_id": None,
                "moderator_role_id": None
            }
            
        return {
            "guild_id": settings.guild_id,
            "transcript_channel_id": settings.transcript_channel_id,
            "moderator_role_id": settings.moderator_role_id
        }

@router.post("/{guild_id}/ticket-settings")
async def update_ticket_settings(guild_id: int, config: TicketSettingsUpdate, is_admin: bool = Depends(verify_guild_admin)):
    """
    Updates the ticket settings for a specific guild.
    """
    async with SessionLocal() as session:
        result = await session.execute(select(TicketSettings).where(TicketSettings.guild_id == guild_id))
        settings = result.scalar_one_or_none()
        
        if not settings:
            settings = TicketSettings(guild_id=guild_id)
            session.add(settings)
            
        if config.transcript_channel_id is not None:
            settings.transcript_channel_id = config.transcript_channel_id
        if config.moderator_role_id is not None:
            settings.moderator_role_id = config.moderator_role_id
            
        await session.commit()
        
        return {"success": True, "message": "Settings updated successfully"}

@router.get("/{guild_id}/channels")
async def get_guild_channels(guild_id: int, is_admin: bool = Depends(verify_guild_admin)):
    bot = api.server.bot_instance
    if not bot:
        raise HTTPException(status_code=503, detail="Bot is offline")
    
    guild = bot.get_guild(guild_id)
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")
        
    channels = [
        {"id": str(c.id), "name": c.name}
        for c in guild.channels
        if isinstance(c, discord.TextChannel)
    ]
    return channels

@router.post("/{guild_id}/send-embed")
async def send_embed(guild_id: int, request: EmbedSendRequest, is_admin: bool = Depends(verify_guild_admin)):
    bot = api.server.bot_instance
    if not bot:
        raise HTTPException(status_code=503, detail="Bot is offline")
        
    guild = bot.get_guild(guild_id)
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")
        
    channel = guild.get_channel(request.channel_id)
    if not channel or not isinstance(channel, discord.TextChannel):
        raise HTTPException(status_code=404, detail="Text channel not found")
        
    try:
        color_val = int(request.color.replace("#", ""), 16) if request.color else discord.Color.default()
        embed = discord.Embed(title=request.title, description=request.description, color=color_val)
        if request.image_url:
            embed.set_image(url=request.image_url)
        
        await channel.send(embed=embed)
        return {"success": True, "message": "Embed sent successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")

@router.get("/{guild_id}/automod-settings")
async def get_automod_settings(guild_id: int, is_admin: bool = Depends(verify_guild_admin)):
    async with SessionLocal() as session:
        result = await session.execute(select(AutoModSettings).where(AutoModSettings.guild_id == guild_id))
        settings = result.scalar_one_or_none()
        
        if not settings:
            return {"guild_id": guild_id, "blacklisted_words": []}
            
        return {"guild_id": settings.guild_id, "blacklisted_words": settings.blacklisted_words}

@router.post("/{guild_id}/automod-settings")
async def update_automod_settings(guild_id: int, config: AutoModSettingsUpdate, is_admin: bool = Depends(verify_guild_admin)):
    async with SessionLocal() as session:
        result = await session.execute(select(AutoModSettings).where(AutoModSettings.guild_id == guild_id))
        settings = result.scalar_one_or_none()
        
        if not settings:
            settings = AutoModSettings(guild_id=guild_id)
            session.add(settings)
            
        settings.blacklisted_words = config.blacklisted_words
        await session.commit()
        return {"success": True, "message": "Automod settings updated"}

@router.get("/{guild_id}/welcome-settings")
async def get_welcome_settings(guild_id: int, is_admin: bool = Depends(verify_guild_admin)):
    async with SessionLocal() as session:
        result = await session.execute(select(WelcomeSettings).where(WelcomeSettings.guild_id == guild_id))
        settings = result.scalar_one_or_none()
        
        if not settings:
            return {"guild_id": guild_id, "channel_id": None, "message": None, "image_url": None}
            
        return {
            "guild_id": settings.guild_id,
            "channel_id": settings.channel_id,
            "message": settings.message,
            "image_url": settings.image_url
        }

@router.post("/{guild_id}/welcome-settings")
async def update_welcome_settings(guild_id: int, config: WelcomeSettingsUpdate, is_admin: bool = Depends(verify_guild_admin)):
    async with SessionLocal() as session:
        result = await session.execute(select(WelcomeSettings).where(WelcomeSettings.guild_id == guild_id))
        settings = result.scalar_one_or_none()
        
        if not settings:
            settings = WelcomeSettings(guild_id=guild_id)
            session.add(settings)
            
        settings.channel_id = config.channel_id
        settings.message = config.message
        settings.image_url = config.image_url
        
        await session.commit()
        return {"success": True, "message": "Welcome settings updated"}
