FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=7860 \
    HOST=0.0.0.0

# Install FFmpeg, libass, and essential fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libass-dev \
    fonts-dejavu-core \
    fonts-freefont-ttf \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application assets and code
COPY . .

# Ensure upload/output directories exist
RUN mkdir -p uploads outputs assets

# Generate sample demo reel on build
RUN python -c "import app; app.ensure_demo_reel_exists()" || true

# Port 7860 is default for Hugging Face Spaces, or dynamic $PORT for Render/Railway
EXPOSE 7860

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-7860}"]
