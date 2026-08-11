# Use official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production

# Set work directory
WORKDIR /app

# Install system dependencies (e.g. for psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md ./
COPY cortexheal/ ./cortexheal/

# Install the application and its dependencies without editable mode
RUN pip install --no-cache-dir .

# Create a non-root user for security and adjust permissions
RUN useradd -m cortexhealuser && chown -R cortexhealuser:cortexhealuser /app
USER cortexhealuser

# Add HEALTHCHECK
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Start Uvicorn server
CMD ["uvicorn", "cortexheal.server.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]