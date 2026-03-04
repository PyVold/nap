FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY services/ai-service/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared libraries
COPY shared /app/shared

# Copy service code
COPY services/ai-service/app /app

EXPOSE 3007

CMD ["python", "main.py"]
