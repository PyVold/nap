FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY services/admin-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared libraries
COPY shared /app/shared

# Copy service code
COPY services/admin-service/app /app

# Expose port
EXPOSE 3005

# Run the service
CMD ["python", "main.py"]
