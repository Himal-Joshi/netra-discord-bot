import asyncio
import os
from dotenv import load_dotenv

from core.bot import Netra
from core.logging import setup_logging
from core.config import settings

import uvicorn
from api.server import app, init_api

async def run_both(bot: Netra):
    # Initialize the API with our bot instance
    init_api(bot)
    
    # Configure uvicorn to run programmatically
    config = uvicorn.Config(app=app, host=settings.DASHBOARD_HOST, port=settings.DASHBOARD_PORT, log_level="info")
    server = uvicorn.Server(config)
    
    # Run both the Discord bot and the Uvicorn web server concurrently
    await asyncio.gather(
        bot.start(settings.DISCORD_TOKEN),
        server.serve()
    )

def main():
    # Setup logging
    setup_logging(level=settings.LOG_LEVEL)

    bot = Netra()

    try:
        asyncio.run(run_both(bot))
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
