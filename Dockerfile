# ==============================================================================
# PromiseCheck Unified Multi-Target Dockerfile
# Targets: 'backend', 'frontend'
# Build Context: Root Directory (.)
# ==============================================================================

# ------------------------------------------------------------------------------
# Target: backend
# ------------------------------------------------------------------------------
FROM python:3.13-slim AS backend

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies from root requirements.txt
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend application source
COPY backend /app

EXPOSE 8000

# Default development command with hot-reload
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ------------------------------------------------------------------------------
# Target: frontend
# ------------------------------------------------------------------------------
FROM node:22-alpine AS frontend

WORKDIR /app

# Install dependencies first
COPY frontend/package*.json ./
RUN npm install

# Copy frontend source code
COPY frontend/ .

EXPOSE 3000

# Default Vite development server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
