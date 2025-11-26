FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY services/api-gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared libraries
COPY shared /app/shared

# Copy service code
COPY services/api-gateway/app /app

# Expose port
EXPOSE 3000

# Run the service
CMD ["python", "main.py"]
