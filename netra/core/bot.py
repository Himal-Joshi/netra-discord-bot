import discord
from discord.ext import commands
import aiohttp
import time
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
        intents.presences = True

        super().__init__(
            command_prefix=commands.when_mentioned_or(settings.BOT_PREFIX),
            intents=intents,
            help_command=None,
        )
        self.session: Optional[aiohttp.ClientSession] = None
        self.start_time = time.time()
        self.db_session_factory = SessionLocal

    async def setup_hook(self) -> None:
        self.session = aiohttp.ClientSession()

        # Initialize Sentry
        if settings.SENTRY_DSN:
            sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=1.0)

        # Start Metrics Server
        start_metrics_server(port=8001)

        # Initialize Database
        await init_db()

        # Load Cogs
        initial_extensions = [
            "cogs.owner.owner",
            "cogs.moderation.moderation",
            "cogs.automod.automod",
            "cogs.utility.utility",
            "cogs.reminders.reminders",
            "cogs.tickets.tickets",
            "cogs.music.music",
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

    async def on_command_completion(self, ctx: commands.Context):
        if ctx.command:
            COMMANDS_EXECUTED.labels(command_name=ctx.command.qualified_name, guild_id=ctx.guild.id if ctx.guild else "DM").inc()
        LATENCY.set(self.latency)

    async def close(self):
        await super().close()
        if self.session:
            await self.session.close()
