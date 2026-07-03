# Configuration Guide

Netra uses Pydantic Settings for structured configuration via environment variables or a `.env` file.

## General Settings
- `DISCORD_TOKEN`: Your bot's token.
- `BOT_PREFIX`: Prefix for text commands (though Slash commands are preferred).
- `OWNER_IDS`: Comma-separated list of Discord User IDs for owner commands.

## Database
- `DATABASE_URL`: SQLAlchemy connection string.
  - SQLite: `sqlite+aiosqlite:///data/netra.db`
  - PostgreSQL: `postgresql+asyncpg://user:password@host:port/db`

## Logging
- `LOG_LEVEL`: One of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`.
- Logs are rotated and stored in the `logs/` directory.

## Metrics
- Metrics are exported on port `8001` for Prometheus.
