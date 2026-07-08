import discord
from discord.ext import commands
import logging
from core.bot import Netra
from database.session import SessionLocal
from models.systems import WelcomeSettings
from sqlalchemy.future import select

log = logging.getLogger(__name__)

class Welcome(commands.Cog):
    def __init__(self, bot: Netra):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        try:
            async with SessionLocal() as session:
                result = await session.execute(select(WelcomeSettings).where(WelcomeSettings.guild_id == member.guild.id))
                settings = result.scalar_one_or_none()
                
                if settings and settings.channel_id:
                    channel = member.guild.get_channel(settings.channel_id)
                    if channel and isinstance(channel, discord.TextChannel):
                        msg = settings.message or "Welcome to the server, {user}!"
                        msg = msg.replace("{user}", member.mention)
                        
                        embed = discord.Embed(
                            title=f"Welcome to {member.guild.name}!",
                            description=msg,
                            color=discord.Color.green()
                        )
                        embed.set_thumbnail(url=member.display_avatar.url)
                        if settings.image_url:
                            embed.set_image(url=settings.image_url)
                            
                        await channel.send(embed=embed)
        except Exception as e:
            log.error(f"Failed to send welcome message: {e}")

async def setup(bot: Netra):
    await bot.add_cog(Welcome(bot))
