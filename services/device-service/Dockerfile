FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (ping for discovery)
RUN apt-get update && apt-get install -y --no-install-recommends \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r appgroup && useradd -r -g appgroup -d /app -s /sbin/nologin appuser

# Install dependencies
COPY services/device-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared libraries
COPY shared /app/shared

# Copy service code
COPY services/device-service/app /app

# Set ownership to non-root user
RUN chown -R appuser:appgroup /app

# Expose port
EXPOSE 3001

# Switch to non-root user
USER appuser

# Run the service with uvicorn directly for better configuration
# Using --timeout-keep-alive to prevent connection drops during long operations
# Using --limit-concurrency to control resource usage
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3001", "--timeout-keep-alive", "75", "--limit-concurrency", "100"]
