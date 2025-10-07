FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for transfer service and video processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    rsync \
    openssh-client \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared utilities (into app directory for proper imports)
COPY shared /app/shared

# Copy backend source
COPY backend .

# Expose port
EXPOSE 8082

# Run backend
CMD ["python", "main.py"]
