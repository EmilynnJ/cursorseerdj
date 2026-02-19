FROM python:3.12-slim-bookworm

# Security: Run as non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Add gunicorn and django-celery-beat for production
RUN pip install --no-cache-dir gunicorn django-celery-beat

# Copy project
COPY . .

# Create staticfiles directory
RUN mkdir -p /app/staticfiles

# Change ownership to non-root user
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health/')" || exit 1

# Default command (overridden by fly.toml processes)
CMD ["gunicorn", "soulseer.wsgi:application", "--bind", "0.0.0.0:8080"]