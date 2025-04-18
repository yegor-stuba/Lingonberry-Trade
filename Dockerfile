FROM python:3.13.3-alpine@sha256:18159b2be11db91f84b8f8f655cd860f805dbd9e49a583ddaac8ab39bf4fe1a7

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install system dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    make \
    g++

# Copy requirements first to leverage Docker cache
COPY setup.py /app/
COPY README.md /app/

# Install Python dependencies
RUN pip install --no-cache-dir -e .
RUN pip install --no-cache-dir pyngrok pytest

# Copy the rest of the application
COPY . /app/

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/charts /app/charts/crypto /app/charts/forex

# Expose ports
EXPOSE 5000

# Set entrypoint
ENTRYPOINT ["python", "-m", "trading_bot.main"]

# Default command
CMD ["--use-ngrok"]