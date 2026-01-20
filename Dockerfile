# Hugging Face Spaces Dockerfile
# Reference: https://huggingface.co/docs/hub/spaces-sdks-docker

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user (required by Hugging Face Spaces)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Set working directory for user
WORKDIR $HOME/app

# Copy requirements first for caching
COPY --chown=user requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=user . .

# Create necessary directories with proper permissions
RUN mkdir -p vector_db cache learning_paths instance

# Make startup script executable
RUN chmod +x start.sh

# Hugging Face Spaces requires port 7860
EXPOSE 7860

# Set environment variables for Hugging Face
ENV PORT=7860
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=web_app:create_app

# Run the startup script (initializes DB then starts gunicorn)
CMD ["bash", "start.sh"]
