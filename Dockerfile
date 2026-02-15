FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    ffmpeg \
    curl \
    git \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency files first
COPY requirements.txt .
COPY package.json .

# Install Dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    npm install --silent

# Copy the rest of the application
COPY . .

# Ensure satele script is executable
RUN chmod +x satele

# Default command (can be overridden by docker-compose)
CMD ["./satele", "start"]
