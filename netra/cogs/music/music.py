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
        self.queues: Dict[int, List[dict]] = {}

    def get_queue(self, guild_id: int) -> List[dict]:
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        return self.queues[guild_id]

    def play_next(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if not vc or not vc.is_connected():
            return

        queue = self.get_queue(interaction.guild.id)
        if not queue:
            # Queue finished
            coro = interaction.channel.send("Queue finished. Waiting for more songs...")
            self.bot.loop.create_task(coro)
            return

        next_song = queue.pop(0)
        
        coro = self._play_song(interaction, next_song['search'], next_song['user'])
        self.bot.loop.create_task(coro)

    async def _play_song(self, interaction: discord.Interaction, search: str, user: str):
        vc = interaction.guild.voice_client
        if not vc or not vc.is_connected():
            return

        try:
            player = await YTDLSource.from_url(search, loop=self.bot.loop, stream=True)
            vc.play(player, after=lambda e: self.play_next(interaction))
            await interaction.channel.send(f'🎵 Now playing: **{player.title}** (Requested by {user})')
        except Exception as e:
            log.error(f"Music error: {e}")
            await interaction.channel.send(f"An error occurred playing the next song: {e}")
            self.play_next(interaction)

    @app_commands.command(name="play", description="Play a song from YouTube or add it to the queue")
    @app_commands.describe(search="The name or URL of the song to play")
    async def play(self, interaction: discord.Interaction, search: str):
        await interaction.response.defer()

        if not interaction.user.voice:
            return await interaction.followup.send("You must be connected to a voice channel.")

        vc = interaction.guild.voice_client
        if not vc:
            vc = await interaction.user.voice.channel.connect()

        queue = self.get_queue(interaction.guild.id)

        if vc.is_playing() or vc.is_paused():
            queue.append({'search': search, 'user': interaction.user.name})
            await interaction.followup.send(f'✅ Added to queue: **{search}** (Position: {len(queue)})')
        else:
            await interaction.followup.send(f'Searching for **{search}**...')
            await self._play_song(interaction, search, interaction.user.name)

    @app_commands.command(name="pause", description="Pause the currently playing song")
    async def pause(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸️ Paused the music.")
        else:
            await interaction.response.send_message("Nothing is currently playing.", ephemeral=True)

    @app_commands.command(name="resume", description="Resume the paused song")
    async def resume(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ Resumed the music.")
        else:
            await interaction.response.send_message("The music is not paused.", ephemeral=True)

    @app_commands.command(name="skip", description="Skip the current song")
    async def skip(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop() # This triggers the 'after' callback which calls play_next
            await interaction.response.send_message("⏭️ Skipped the current song.")
        else:
            await interaction.response.send_message("Nothing to skip.", ephemeral=True)

    @app_commands.command(name="queue", description="View the upcoming songs in the queue")
    async def queue(self, interaction: discord.Interaction):
        queue = self.get_queue(interaction.guild.id)
        if not queue:
            return await interaction.response.send_message("The queue is currently empty.", ephemeral=True)
            
        embed = discord.Embed(title=f"Music Queue for {interaction.guild.name}", color=discord.Color.blurple())
        
        queue_text = ""
        for i, song in enumerate(queue[:10]): # Show top 10
            queue_text += f"**{i+1}.** {song['search']} *(Req by {song['user']})*\n"
            
        if len(queue) > 10:
            queue_text += f"\n*...and {len(queue) - 10} more songs.*"
            
        embed.description = queue_text
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="end", description="Stop the music, clear the queue, and disconnect")
    async def end(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        self.get_queue(interaction.guild.id).clear()
        
        if vc:
            await vc.disconnect()
            await interaction.response.send_message("🛑 Stopped the music, cleared the queue, and disconnected.")
        else:
            await interaction.response.send_message("I am not in a voice channel.", ephemeral=True)

async def setup(bot: Netra):
    await bot.add_cog(Music(bot))
