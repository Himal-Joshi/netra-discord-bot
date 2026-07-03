# Installation Guide

## Prerequisites
- Python 3.12+
- FFmpeg (for music)
- SQLite (default) or PostgreSQL

## Steps
1. **Clone the Repo**:
   ```bash
   git clone <repo_url>
   cd netra
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**:
   - Copy `.env.example` to `.env`.
   - Fill in your `DISCORD_TOKEN`, `CLIENT_ID`, and `CLIENT_SECRET`.

4. **Run the Bot**:
   ```bash
   python launcher.py
   ```

## Docker Installation
1. Build the image:
   ```bash
   docker-compose build
   ```
2. Start the services:
   ```bash
   docker-compose up -d
   ```
