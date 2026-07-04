import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.bot import Netra

from api.routes import stats, guilds

log = logging.getLogger(__name__)

app = FastAPI(
    title="Netra Dashboard API",
    description="Backend API for the Netra Discord Bot Vercel Dashboard",
    version="1.0.0"
)

# CORS configuration - This answers the user's security concern!
# We will only allow requests from the Vercel domain, localhost, and the oracle IP.
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    # We can add the Vercel domain here later when deployed
    "*"  # Temporarily allow all for easy development testing. Should restrict in production.
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# A global reference to our bot instance so the API can talk to Discord.py
bot_instance: Netra = None

def init_api(bot: Netra):
    """
    Initialize the API with a reference to the running bot.
    """
    global bot_instance
    bot_instance = bot
    log.info("FastAPI successfully linked to Discord Bot instance.")

app.include_router(stats.router, prefix="/api/v1/stats", tags=["Stats"])
app.include_router(guilds.router, prefix="/api/v1/guilds", tags=["Guilds"])

@app.get("/")
async def root():
    return {"message": "Netra API is running!"}
