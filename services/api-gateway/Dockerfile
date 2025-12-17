FROM python:3.11-slim

WORKDIR /app

# Create non-root user for security
RUN groupadd -r appgroup && useradd -r -g appgroup -d /app -s /sbin/nologin appuser

# Install dependencies
COPY services/api-gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared libraries
COPY shared /app/shared

# Copy service code
COPY services/api-gateway/app /app

# Set ownership to non-root user
RUN chown -R appuser:appgroup /app

# Expose port
EXPOSE 3000

# Switch to non-root user
USER appuser

# Run the service
CMD ["python", "main.py"]
