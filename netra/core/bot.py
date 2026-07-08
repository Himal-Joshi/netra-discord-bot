import discord
from discord.ext import commands, tasks
import aiohttp
import time
import wavelink
from typing import List, Optional
import logging

import sentry_sdk
from core.config import settings
from database.session import SessionLocal, init_db
from core.metrics import GUILD_COUNT, LATENCY, COMMANDS_EXECUTED, start_metrics_server
from core.i18n import i18n

log = logging.getLogger(__name__)

class Netra(commands.AutoShardedBot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True

        super().__init__(
            command_prefix=commands.when_mentioned_or(settings.BOT_PREFIX),
            intents=intents,
            help_command=None,
            chunk_guilds_at_startup=False,
            max_messages=100,
            member_cache_flags=discord.MemberCacheFlags.from_intents(intents),
        )
        self.session: Optional[aiohttp.ClientSession] = None
        self.start_time = time.time()
        self.db_session_factory = SessionLocal

    async def setup_hook(self) -> None:
        self.session = aiohttp.ClientSession()

        # Initialize Sentry
        if settings.SENTRY_DSN:
            sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=0.1)

        # Start Metrics Server
        start_metrics_server(port=8001)

        # Initialize Database
        await init_db()

        # Connect to Lavalink
        try:
            nodes = [wavelink.Node(
                uri=f"http://{settings.LAVALINK_HOST}:{settings.LAVALINK_PORT}",
                password=settings.LAVALINK_PASSWORD,
            )]
            await wavelink.Pool.connect(nodes=nodes, client=self, cache_capacity=100)
            log.info(f"Connected to Lavalink at {settings.LAVALINK_HOST}:{settings.LAVALINK_PORT}")
        except Exception as e:
            log.error(f"Failed to connect to Lavalink: {e}. Music features will be unavailable.")

        initial_extensions = [
            "cogs.owner.owner",
            "cogs.moderation.moderation",
            "cogs.automod.automod",
            "cogs.utility.utility",
            "cogs.reminders.reminders",
            "cogs.tickets.tickets",
            "cogs.music.music",
            "cogs.welcome.welcome",
        ]

        for ext in initial_extensions:
            try:
                await self.load_extension(ext)
                log.info(f"Loaded extension: {ext}")
            except Exception as e:
                log.error(f"Failed to load extension {ext}: {e}", exc_info=True)

    async def on_ready(self):
        if self.user:
            log.info(f"Logged in as {self.user} (ID: {self.user.id})")
        log.info(f"Connected to {len(self.guilds)} guilds")
        GUILD_COUNT.set(len(self.guilds))
        
        # Set the "Listening to /help" status
        activity = discord.Activity(type=discord.ActivityType.listening, name="/help")
        await self.change_presence(activity=activity)

        # Start the background metrics loop
        if not self.update_metrics.is_running():
            self.update_metrics.start()

    @tasks.loop(seconds=30)
    async def update_metrics(self):
        """Update Prometheus metrics in the background instead of per-command."""
        LATENCY.set(self.latency)
        GUILD_COUNT.set(len(self.guilds))

    @update_metrics.before_loop
    async def before_update_metrics(self):
        await self.wait_until_ready()

    async def on_command_completion(self, ctx: commands.Context):
        if ctx.command:
            COMMANDS_EXECUTED.labels(command_name=ctx.command.qualified_name, guild_id=ctx.guild.id if ctx.guild else "DM").inc()

    async def close(self):
        await super().close()
        if self.session:
            await self.session.close()
