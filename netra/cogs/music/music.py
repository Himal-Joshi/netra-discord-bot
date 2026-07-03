import discord
import asyncio
import yt_dlp
from discord.ext import commands
from discord import app_commands
import logging
from typing import List, Dict

from core.bot import Netra

log = logging.getLogger(__name__)

# yt-dlp configuration
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(YDL_OPTIONS)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **FFMPEG_OPTIONS), data=data)

class Music(commands.Cog):
    def __init__(self, bot: Netra):
        self.bot = bot
        self.queues: Dict[int, List] = {}

    @app_commands.command(name="play", description="Play a song from YouTube")
    async def play(self, interaction: discord.Interaction, search: str):
        await interaction.response.defer()

        if not interaction.user.voice:
            return await interaction.followup.send("You are not connected to a voice channel.")

        vc = interaction.guild.voice_client
        if not vc:
            vc = await interaction.user.voice.channel.connect()

        try:
            player = await YTDLSource.from_url(search, loop=self.bot.loop, stream=True)
            vc.play(player, after=lambda e: log.error(f'Player error: {e}') if e else None)
            await interaction.followup.send(f'Now playing: **{player.title}**')
        except Exception as e:
            log.error(f"Music error: {e}")
            await interaction.followup.send(f"An error occurred: {e}")

    @app_commands.command(name="stop", description="Stop the music and disconnect")
    async def stop(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc:
            await vc.disconnect()
            await interaction.response.send_message("Stopped the music and disconnected.")
        else:
            await interaction.response.send_message("Not playing anything.")

async def setup(bot: Netra):
    await bot.add_cog(Music(bot))
