FROM python:3.12-slim

# Set environment variables.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create app directory.
WORKDIR /app

# Install system dependencies.
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies.
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application code.
COPY bot/ ./bot/

# Create data directory.
RUN mkdir -p /app/data

# Create non-root user.
RUN groupadd -r yogabot && useradd -r -g yogabot yogabot
RUN chown -R yogabot:yogabot /app
USER yogabot

# Health check.
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/healthz || exit 1

# Expose HTTP port.
EXPOSE 8080

# Run the application.
CMD ["python", "-m", "bot.main"] 