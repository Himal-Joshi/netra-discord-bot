from fastapi import APIRouter
import api.server

router = APIRouter()

@router.get("/")
async def get_stats():
    """
    Returns live bot statistics directly from the running bot instance.
    """
    bot = api.server.bot_instance
    
    if not bot:
        return {
            "status": "offline",
            "server_count": 0,
            "member_count": 0,
            "ping": 0
        }
        
    member_count = sum(guild.member_count for guild in bot.guilds if guild.member_count)
    
    return {
        "status": "online",
        "server_count": len(bot.guilds),
        "member_count": member_count,
        "ping": round(bot.latency * 1000)
    }
