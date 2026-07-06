import discord
import asyncio
import yt_dlp
import shutil
import os
from discord.ext import commands, tasks
from discord import app_commands
import logging
from typing import List, Dict, Optional

from core.bot import Netra

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FFmpeg resolution — works locally on Windows and inside Docker
# ---------------------------------------------------------------------------
def _find_ffmpeg() -> str:
    """Return the ffmpeg executable path. Checks PATH first, then common Windows dirs."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    candidates = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    raise FileNotFoundError(
        "ffmpeg was not found. Install ffmpeg and make sure it is on your PATH.\n"
        "Download: https://ffmpeg.org/download.html"
    )

FFMPEG_EXECUTABLE = _find_ffmpeg()
log.info(f"Using ffmpeg: {FFMPEG_EXECUTABLE}")

# yt-dlp options
# Android player client bypasses YouTube bot-detection on data-center IPs.
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'source_address': '0.0.0.0',
    'socket_timeout': 30,
    'extractor_args': {
        'youtube': {
            'player_client': ['ios', 'android', 'web'],
        }
    },
}

FFMPEG_OPTIONS = {
    'executable': FFMPEG_EXECUTABLE,
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -bufsize 64k',
}

# Auto-disconnect timeouts (seconds)
INACTIVITY_TIMEOUT = 120   # nothing playing for 2 min → leave
ALONE_TIMEOUT = 120        # bot is alone in VC for 2 min → leave


# ---------------------------------------------------------------------------
# YTDL audio source
# ---------------------------------------------------------------------------
class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()

        # ── Step 1: Resolve search query → direct video URL ───────────────
        # For text queries we do a fast flat search first (no bot-check needed).
        # Direct YouTube/http URLs skip this step entirely.
        if not url.startswith('http'):
            search_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,      # only fetch metadata, not the stream
                'noplaylist': True,
                'socket_timeout': 30,
                'default_search': 'ytsearch',
            }
            search_ytdl = yt_dlp.YoutubeDL(search_opts)
            search_data = await loop.run_in_executor(
                None, lambda: search_ytdl.extract_info(f'ytsearch1:{url}', download=False)
            )

            if not search_data:
                raise Exception(f"No results found for **{url}**.")

            entries = list(search_data.get('entries') or [])
            if not entries or entries[0] is None:
                raise Exception(f"No results found for **{url}**.")

            first = entries[0]
            # Build a proper YouTube watch URL from whatever identifier we have
            video_id = first.get('id') or first.get('url', '')
            if video_id.startswith('http'):
                url = video_id
            else:
                url = f'https://www.youtube.com/watch?v={video_id}'

        # ── Step 2: Extract the real audio stream URL from the video URL ──
        # iOS/Android player clients bypass bot-detection on server IPs
        # without needing cookies or a signed-in account.
        ytdl = yt_dlp.YoutubeDL(YDL_OPTIONS)
        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(url, download=not stream)
        )

        if data is None:
            raise Exception("Could not load song info. Try again.")

        # Shouldn't happen with noplaylist=True, but handle it anyway
        if 'entries' in data:
            entries = list(data['entries'])
            if not entries or entries[0] is None:
                raise Exception("Could not load song info. Try again.")
            data = entries[0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **FFMPEG_OPTIONS), data=data)



# ---------------------------------------------------------------------------
# Per-guild music state
# ---------------------------------------------------------------------------
class GuildMusicState:
    def __init__(self):
        self.queue: List[dict] = []
        self.idle_since: Optional[float] = None   # when queue became empty
        self.alone_since: Optional[float] = None  # when bot became alone
        self.text_channel: Optional[discord.TextChannel] = None


# ---------------------------------------------------------------------------
# Music Cog
# ---------------------------------------------------------------------------
class Music(commands.Cog):
    def __init__(self, bot: Netra):
        self.bot = bot
        self.states: Dict[int, GuildMusicState] = {}
        self._inactivity_check.start()

    def cog_unload(self):
        self._inactivity_check.cancel()

    # ── State helpers ───────────────────────────────────────────────────────

    def get_state(self, guild_id: int) -> GuildMusicState:
        if guild_id not in self.states:
            self.states[guild_id] = GuildMusicState()
        return self.states[guild_id]

    def get_queue(self, guild_id: int) -> List[dict]:
        return self.get_state(guild_id).queue

    # ── Playback ────────────────────────────────────────────────────────────

    def play_next(self, guild: discord.Guild, text_channel: discord.abc.Messageable):
        """Called from the 'after' callback when a song finishes."""
        vc = guild.voice_client
        if not vc or not vc.is_connected():
            return

        state = self.get_state(guild.id)
        state.text_channel = text_channel

        if not state.queue:
            log.info(f"[{guild.name}] Queue empty — starting inactivity timer.")
            state.idle_since = self.bot.loop.time()
            coro = text_channel.send(
                "⏹️ Queue finished. Waiting for more songs… "
                "*(I'll leave in 2 min if nothing is added)*"
            )
            self.bot.loop.create_task(coro)
            return

        state.idle_since = None
        next_song = state.queue.pop(0)
        coro = self._play_song(guild, text_channel, next_song['search'], next_song['user'])
        self.bot.loop.create_task(coro)

    async def _play_song(
        self,
        guild: discord.Guild,
        text_channel: discord.abc.Messageable,
        search: str,
        user: str,
    ):
        vc = guild.voice_client
        if not vc or not vc.is_connected():
            return

        state = self.get_state(guild.id)
        state.idle_since = None

        try:
            player = await YTDLSource.from_url(search, loop=self.bot.loop, stream=True)
            vc.play(
                player,
                after=lambda e: (
                    log.error(f"[{guild.name}] Playback error: {e}") if e else None,
                    self.play_next(guild, text_channel),
                )[-1],
            )
            await text_channel.send(f"🎵 Now playing: **{player.title}** *(requested by {user})*")
        except Exception as e:
            log.error(f"[{guild.name}] Error playing song: {e}")
            await text_channel.send(f"❌ An error occurred: {e}")
            self.play_next(guild, text_channel)

    # ── Background task: auto-disconnect ───────────────────────────────────

    @tasks.loop(seconds=30)
    async def _inactivity_check(self):
        """Every 30 s, check every guild for inactivity or loneliness."""
        now = self.bot.loop.time()

        for guild in self.bot.guilds:
            vc = guild.voice_client
            if not vc or not vc.is_connected():
                continue

            state = self.get_state(guild.id)

            # ── Inactivity (queue empty + not playing) ───────────────────
            if not vc.is_playing() and not vc.is_paused():
                if state.idle_since is None:
                    state.idle_since = now
                elif now - state.idle_since >= INACTIVITY_TIMEOUT:
                    log.info(f"[{guild.name}] Auto-disconnect: idle for 2 min.")
                    state.queue.clear()
                    state.idle_since = None
                    state.alone_since = None
                    if state.text_channel:
                        await state.text_channel.send(
                            "👋 Leaving the voice channel due to **2 minutes of inactivity**."
                        )
                    await vc.disconnect()
                    continue  # skip alone check for this guild
            else:
                state.idle_since = None  # actively playing

            # ── Alone check (no humans in channel) ───────────────────────
            if vc.channel:
                humans = [m for m in vc.channel.members if not m.bot]
                if not humans:
                    if state.alone_since is None:
                        state.alone_since = now
                    elif now - state.alone_since >= ALONE_TIMEOUT:
                        log.info(f"[{guild.name}] Auto-disconnect: alone for 2 min.")
                        state.queue.clear()
                        state.idle_since = None
                        state.alone_since = None
                        if vc.is_playing():
                            vc.stop()
                        if state.text_channel:
                            await state.text_channel.send(
                                "👋 Everyone left the voice channel, so I'm leaving too. See you next time!"
                            )
                        await vc.disconnect()
                else:
                    state.alone_since = None  # humans present

    @_inactivity_check.before_loop
    async def _before_inactivity_check(self):
        await self.bot.wait_until_ready()

    # ── Voice state listener — reset alone timer on join ───────────────────

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        guild = member.guild
        vc = guild.voice_client
        if not vc or not vc.is_connected() or not vc.channel:
            return

        state = self.get_state(guild.id)
        humans = [m for m in vc.channel.members if not m.bot]
        if humans:
            state.alone_since = None  # someone is here — reset timer

    # ── Slash commands ──────────────────────────────────────────────────────

    @app_commands.command(name="play", description="Play a song from YouTube or add it to the queue")
    @app_commands.describe(search="Song name or YouTube URL")
    async def play(self, interaction: discord.Interaction, search: str):
        await interaction.response.defer()

        if not interaction.user.voice:
            return await interaction.followup.send("❌ You must be in a voice channel first.")

        vc = interaction.guild.voice_client
        if not vc:
            vc = await interaction.user.voice.channel.connect()

        state = self.get_state(interaction.guild.id)
        state.text_channel = interaction.channel
        state.idle_since = None
        state.alone_since = None

        if vc.is_playing() or vc.is_paused():
            state.queue.append({'search': search, 'user': interaction.user.name})
            await interaction.followup.send(f"✅ Added to queue: **{search}** (Position: {len(state.queue)})")
        else:
            await interaction.followup.send(f"🔍 Searching for **{search}**…")
            await self._play_song(interaction.guild, interaction.channel, search, interaction.user.name)

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
            state = self.get_state(interaction.guild.id)
            state.idle_since = None
            await interaction.response.send_message("▶️ Resumed the music.")
        else:
            await interaction.response.send_message("The music is not paused.", ephemeral=True)

    @app_commands.command(name="skip", description="Skip the current song")
    async def skip(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()  # triggers 'after' callback → play_next
            await interaction.response.send_message("⏭️ Skipped the current song.")
        else:
            await interaction.response.send_message("Nothing to skip.", ephemeral=True)

    @app_commands.command(name="queue", description="View the upcoming songs in the queue")
    async def queue(self, interaction: discord.Interaction):
        queue = self.get_queue(interaction.guild.id)
        if not queue:
            return await interaction.response.send_message("The queue is currently empty.", ephemeral=True)

        embed = discord.Embed(
            title=f"Music Queue — {interaction.guild.name}",
            color=discord.Color.blurple(),
        )
        lines = ""
        for i, song in enumerate(queue[:10]):
            lines += f"**{i+1}.** {song['search']} *(req by {song['user']})*\n"
        if len(queue) > 10:
            lines += f"\n*…and {len(queue) - 10} more songs.*"
        embed.description = lines
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="end", description="Stop music, clear queue, and disconnect")
    async def end(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        state = self.get_state(interaction.guild.id)
        state.queue.clear()
        state.idle_since = None
        state.alone_since = None

        if vc:
            if vc.is_playing():
                vc.stop()
            await vc.disconnect()
            await interaction.response.send_message("🛑 Stopped music, cleared the queue, and disconnected.")
        else:
            await interaction.response.send_message("I'm not in a voice channel.", ephemeral=True)


async def setup(bot: Netra):
    await bot.add_cog(Music(bot))
