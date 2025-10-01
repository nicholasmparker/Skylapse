FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for transfer service
RUN apt-get update && apt-get install -y --no-install-recommends \
    rsync \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared utilities
COPY shared /shared

# Copy backend source
COPY backend .

# Expose port
EXPOSE 8082

# Run backend
CMD ["python", "main.py"]
