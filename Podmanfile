FROM python:3.9-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update -qq && \
    apt-get install -qq -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --quiet -r requirements.txt

FROM python:3.9-slim

WORKDIR /app

# Install runtime dependencies
RUN pip install --no-cache-dir gunicorn

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages

# Copy application files
COPY . .

# Create data directory
RUN mkdir -p /app/data

# Make entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Create volume for persistent data
VOLUME ["/app/data"]

# Set environment variables
ENV FLASK_APP=app.py \
    DATABASE=/app/data/therapy.db \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    TOKENIZERS_PARALLELISM=true \
    LLAMA_INDEX_CACHE_DIR=/app/data/llama_index_cache \
    OPENAI_API_KEY=${OPENAI_API_KEY}

# Expose port
EXPOSE 5000

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
