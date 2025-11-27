FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (ping for discovery)
RUN apt-get update && apt-get install -y --no-install-recommends \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY services/device-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared libraries
COPY shared /app/shared

# Copy service code
COPY services/device-service/app /app

# Expose port
EXPOSE 3001

# Run the service
CMD ["python", "main.py"]
