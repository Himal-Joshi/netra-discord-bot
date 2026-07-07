import asyncio
import discord
import wavelink
from typing import Optional, cast
from discord.ext import commands
from discord import app_commands
import logging

from core.bot import Netra

log = logging.getLogger(__name__)

# Seconds bot waits alone in VC before disconnecting
ALONE_TIMEOUT = 120


class Music(commands.Cog):
    def __init__(self, bot: Netra):
        self.bot = bot
        # Track per-guild "alone" disconnect tasks
        self._alone_tasks: dict[int, asyncio.Task] = {}

    def cog_unload(self):
        for task in self._alone_tasks.values():
            task.cancel()

    # ── Internal helpers ────────────────────────────────────────────────────

    def _cancel_alone_task(self, guild_id: int):
        task = self._alone_tasks.get(guild_id)
        if task and not task.done():
            task.cancel()
        self._alone_tasks.pop(guild_id, None)

    def _start_alone_task(self, player: wavelink.Player):
        guild_id = player.guild.id
        self._cancel_alone_task(guild_id)
        self._alone_tasks[guild_id] = asyncio.create_task(
            self._alone_disconnect(player)
        )

    async def _alone_disconnect(self, player: wavelink.Player):
        await asyncio.sleep(ALONE_TIMEOUT)
        if not player.connected:
            return
        channel: Optional[discord.TextChannel] = getattr(player, 'text_channel', None)
        if channel:
            await channel.send(
                "👋 Everyone left the voice channel — disconnecting. See you next time!"
            )
        log.info(f"[{player.guild.name}] Auto-disconnect: alone for {ALONE_TIMEOUT}s.")
        await player.disconnect()

    # ── Wavelink events ─────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        player: wavelink.Player = payload.player
        track: wavelink.Playable = payload.track
        channel: Optional[discord.TextChannel] = getattr(player, 'text_channel', None)
        if channel:
            requester = getattr(track.extras, 'requester', 'Unknown')
            await channel.send(
                f"🎵 Now playing: **{track.title}** by {track.author} "
                f"*(requested by {requester})*"
            )

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player: wavelink.Player = payload.player
        channel: Optional[discord.TextChannel] = getattr(player, 'text_channel', None)

        # payload.reason is an enum; get its string value safely across wavelink versions
        reason_val = getattr(payload.reason, 'value', str(payload.reason))
        log.debug(f"[{player.guild.name}] Track ended — reason: {reason_val}")

        # Tell user if the track failed to load/stream
        if "loadFailed" in reason_val or "load_failed" in reason_val.lower():
            if channel:
                await channel.send(
                    f"❌ Failed to stream **{payload.track.title}**. "
                    "YouTube blocked this track on the server IP. Try a different song."
                )

        # Announce queue-empty only on normal finish (not skip/stop/replace)
        if (
            not player.queue
            and not player.playing
            and not any(r in reason_val.lower() for r in ("replaced", "stopped"))
        ):
            if channel:
                await channel.send(
                    "⏹️ Queue finished. Waiting for more songs… "
                    "*(I'll leave in 2 min if nothing is added)*"
                )

    @commands.Cog.listener()
    async def on_wavelink_inactive_player(self, player: wavelink.Player):
        """Fired by wavelink after player.inactive_timeout seconds of silence."""
        channel: Optional[discord.TextChannel] = getattr(player, 'text_channel', None)
        if channel:
            await channel.send(
                "👋 Leaving the voice channel due to **2 minutes of inactivity**."
            )
        log.info(f"[{player.guild.name}] Auto-disconnect: inactive for {player.inactive_timeout}s.")
        self._cancel_alone_task(player.guild.id)
        await player.disconnect()

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        """Detect when bot is left alone and start/cancel the alone timer."""
        guild = member.guild
        vc = guild.voice_client
        if not vc or not isinstance(vc, wavelink.Player) or not vc.channel:
            return

        humans = [m for m in vc.channel.members if not m.bot]
        if not humans:
            self._start_alone_task(vc)
        else:
            self._cancel_alone_task(guild.id)

    # ── Slash commands ──────────────────────────────────────────────────────

    @app_commands.command(name="play", description="Play a song from YouTube or add it to the queue")
    @app_commands.describe(search="Song name or YouTube URL")
    @app_commands.guild_only()
    async def play(self, interaction: discord.Interaction, search: str):
        await interaction.response.defer()

        guild = interaction.guild
        member = interaction.user
        if guild is None or not isinstance(member, discord.Member):
            return await interaction.followup.send("❌ This command can only be used in a server.")

        if not member.voice or not member.voice.channel:
            return await interaction.followup.send("❌ You must be in a voice channel first.")

        voice_channel = member.voice.channel

        player: wavelink.Player
        existing_vc = guild.voice_client

        # Force-disconnect stale non-wavelink voice clients (leftover from old sessions)
        if existing_vc and not isinstance(existing_vc, wavelink.Player):
            await existing_vc.disconnect(force=True)
            existing_vc = None

        if not existing_vc:
            try:
                player = cast(wavelink.Player, await voice_channel.connect(
                    cls=wavelink.Player,
                    self_deaf=True,
                ))
            except Exception as e:
                return await interaction.followup.send(
                    f"❌ Could not connect to voice channel: {e}"
                )
            player.autoplay = wavelink.AutoPlayMode.partial
            player.inactive_timeout = ALONE_TIMEOUT
            await player.set_volume(100)  # explicit 100% — avoids Lavalink default being quiet
        else:
            player = cast(wavelink.Player, existing_vc)

        player.text_channel = interaction.channel
        self._cancel_alone_task(guild.id)

        # Use SoundCloud for searches (no bot-detection on server IPs).
        # Direct YouTube/HTTP URLs are passed through as-is.
        is_url = search.startswith(("http://", "https://"))
        try:
            if is_url:
                tracks: wavelink.Search = await wavelink.Playable.search(search)
            else:
                tracks: wavelink.Search = await wavelink.Playable.search(
                    search, source=wavelink.TrackSource.SoundCloud
                )
        except Exception as e:
            log.error(f"[{guild.name}] Search error: {e}")
            return await interaction.followup.send(f"❌ Search failed: {e}")

        if not tracks:
            return await interaction.followup.send(f"❌ No results found for **{search}**.")

        track: wavelink.Playable = tracks[0]

        # Attach requester info to the track (shown in on_wavelink_track_start)
        track.extras.requester = member.name

        if player.playing or player.paused:
            player.queue.put(track)
            await interaction.followup.send(
                f"✅ Added to queue: **{track.title}** "
                f"*(Position: {len(player.queue)})*"
            )
        else:
            await player.play(track)
            # Don't announce here — on_wavelink_track_start will do it
            await interaction.followup.send(f"🔍 Loading **{track.title}**…")

    @app_commands.command(name="pause", description="Pause the currently playing song")
    @app_commands.guild_only()
    async def pause(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        player: wavelink.Player = interaction.guild.voice_client  # type: ignore
        if not player or not player.playing:
            return await interaction.response.send_message(
                "Nothing is currently playing.", ephemeral=True
            )
        await player.pause(True)
        await interaction.response.send_message("⏸️ Paused the music.")

    @app_commands.command(name="resume", description="Resume the paused song")
    @app_commands.guild_only()
    async def resume(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        player: wavelink.Player = interaction.guild.voice_client  # type: ignore
        if not player or not player.paused:
            return await interaction.response.send_message(
                "The music is not paused.", ephemeral=True
            )
        await player.pause(False)
        await interaction.response.send_message("▶️ Resumed the music.")

    @app_commands.command(name="skip", description="Skip the current song")
    @app_commands.guild_only()
    async def skip(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        player: wavelink.Player = interaction.guild.voice_client  # type: ignore
        if not player or (not player.playing and not player.paused):
            return await interaction.response.send_message("Nothing to skip.", ephemeral=True)
        await player.skip(force=True)
        await interaction.response.send_message("⏭️ Skipped the current song.")

    @app_commands.command(name="queue", description="View the upcoming songs in the queue")
    @app_commands.guild_only()
    async def queue(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        player: wavelink.Player = interaction.guild.voice_client  # type: ignore
        if not player or not player.queue:
            return await interaction.response.send_message(
                "The queue is currently empty.", ephemeral=True
            )

        embed = discord.Embed(
            title=f"Music Queue — {interaction.guild.name}",
            color=discord.Color.blurple(),
        )
        lines = ""
        for i, track in enumerate(list(player.queue)[:10]):
            requester = getattr(track.extras, 'requester', '?')
            lines += f"**{i+1}.** {track.title} — {track.author} *(req by {requester})*\n"
        if len(player.queue) > 10:
            lines += f"\n*…and {len(player.queue) - 10} more songs.*"
        embed.description = lines
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="end", description="Stop music, clear queue, and disconnect")
    @app_commands.guild_only()
    async def end(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return
        player: wavelink.Player = interaction.guild.voice_client  # type: ignore
        if not player:
            return await interaction.response.send_message(
                "I'm not in a voice channel.", ephemeral=True
            )
        self._cancel_alone_task(interaction.guild.id)
        player.queue.clear()
        await player.disconnect()
        await interaction.response.send_message(
            "🛑 Stopped music, cleared the queue, and disconnected."
        )


async def setup(bot: Netra):
    await bot.add_cog(Music(bot))
