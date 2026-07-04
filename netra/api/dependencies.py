import aiohttp
from fastapi import Request, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_discord_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """
    Validates the Discord access token passed in the Authorization header.
    Returns the user profile from Discord.
    """
    token = credentials.credentials
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get("https://discord.com/api/v10/users/@me", headers=headers) as resp:
            if resp.status != 200:
                raise HTTPException(status_code=401, detail="Invalid or expired Discord access token")
            return await resp.json()

async def get_user_guilds(credentials: HTTPAuthorizationCredentials = Security(security)) -> list:
    """
    Fetches the list of guilds the user is in using their access token.
    """
    token = credentials.credentials
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get("https://discord.com/api/v10/users/@me/guilds", headers=headers) as resp:
            if resp.status != 200:
                raise HTTPException(status_code=401, detail="Could not fetch user guilds")
            return await resp.json()

async def verify_guild_admin(guild_id: int, guilds: list = Security(get_user_guilds)):
    """
    Dependency to verify the user has Administrator or Manage Guild permissions for a specific guild.
    """
    # Permissions bitwise flags in Discord
    ADMINISTRATOR = 0x8
    MANAGE_GUILD = 0x20
    
    for guild in guilds:
        if str(guild["id"]) == str(guild_id):
            permissions = int(guild.get("permissions", 0))
            if (permissions & ADMINISTRATOR) == ADMINISTRATOR or (permissions & MANAGE_GUILD) == MANAGE_GUILD:
                return True
            raise HTTPException(status_code=403, detail="You do not have permission to manage this server.")
            
    raise HTTPException(status_code=403, detail="You are not in this server or do not have access.")
