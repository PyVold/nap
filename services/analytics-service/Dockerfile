FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY services/analytics-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared libraries
COPY shared /app/shared

# Copy service code
COPY services/analytics-service/app /app

# Expose port
EXPOSE 3006

# Run the service
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3006"]
