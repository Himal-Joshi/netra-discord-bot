# Netra

Netra (नेत्र) means "Leader", "Guide", "Eye that Watches", and "One who Oversees."

A modern intelligent guardian of Discord communities. Built with Clean Architecture, SOLID principles, and a modular design.

## Features

- **Moderation**: Advanced moderation tools with AutoMod, Anti-Spam, and Anti-Raid.
- **Utility**: Comprehensive server management and utility commands.
- **Reminder System**: Natural language parsing for persistent reminders.
- **Music**: High-quality music playback with session restoration.
- **Tickets**: Button-based ticket system with transcript generation.
- **Dashboard**: FastAPI-based web dashboard for configuration.
- **Localization**: Multi-language support using Fluent.
- **Metrics**: Integrated Prometheus metrics.

## Tech Stack

- Python 3.12+
- discord.py
- SQLAlchemy (Async)
- FastAPI
- PostgreSQL / SQLite
- Docker & Docker Compose

## Quick Start

### Prerequisites
- Python 3.12 or higher
- A Discord Bot Token (Get this from the [Discord Developer Portal](https://discord.com/developers/applications))
- Git

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/netra-discord-bot.git
   cd netra-discord-bot/netra
   ```

2. **Configure Environment Variables:**
   Rename `.env.example` to `.env` and fill in your private details:
   ```env
   DISCORD_TOKEN=your_secret_bot_token_here
   DATABASE_URL=sqlite+aiosqlite:///data/netra.db
   OWNER_ID=your_discord_user_id
   COMMAND_PREFIX=n!
   ```

3. **Install dependencies:**
   It is highly recommended to use a virtual environment (`venv` or `conda`).
   ```bash
   pip install -r requirements.txt
   pip install PyNaCl
   ```

4. **Run the bot:**
   ```bash
   python launcher.py
   ```

5. **Sync Slash Commands:**
   Once the bot is online and invited to your server, type `n!sync` in a channel to register the slash commands (`/ping`, `/serverinfo`, etc.).

## Hosting

Netra is designed to run 24/7 on a cloud server (VPS) running Ubuntu or another Linux distribution. You can use tools like `tmux`, `screen`, or `pm2` to keep the bot process alive in the background.

Refer to the `docs/` directory for detailed documentation.
