import asyncio
import os
from dotenv import load_dotenv

from core.bot import Netra
from core.logging import setup_logging
from core.config import settings

def main():
    # Setup logging
    setup_logging(level=settings.LOG_LEVEL)

    bot = Netra()

    try:
        asyncio.run(bot.start(settings.DISCORD_TOKEN))
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
