from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import Optional

from database.session import SessionLocal
from models.systems import TicketSettings
from api.dependencies import verify_guild_admin

router = APIRouter()

class TicketSettingsUpdate(BaseModel):
    transcript_channel_id: Optional[int] = None
    moderator_role_id: Optional[int] = None

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
