FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY netra/requirements.txt /app/netra/requirements.txt
RUN pip install --no-cache-dir -r /app/netra/requirements.txt

# Copy project (maintaining package structure)
COPY netra /app/netra

# Create log directory
RUN mkdir -p /app/netra/logs

# Run the bot using module notation
CMD ["python", "-m", "netra.launcher"]
