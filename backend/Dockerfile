# Skylapse Real-Time Backend - Production Dockerfile
# Professional Mountain Timelapse Camera System

FROM python:3.11-slim-bullseye AS base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN groupadd -r skylapse && useradd -r -g skylapse skylapse

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Set ownership
RUN chown -R skylapse:skylapse /app

# Switch to non-root user
USER skylapse

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8082/health || exit 1

# Expose port
EXPOSE 8082

# Set environment variables
ENV PYTHONPATH=/app
ENV REALTIME_HOST=0.0.0.0
ENV REALTIME_PORT=8082
ENV JWT_SECRET=skylapse_jwt_secret_change_in_production

# Run the real-time server
CMD ["python", "-m", "src.realtime_server"]
