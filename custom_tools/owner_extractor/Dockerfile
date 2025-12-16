# Owner Extractor Service Dockerfile
FROM mcr.microsoft.com/playwright/python:v1.41.0-jammy

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY owner_extractor.py .
COPY api.py .

# Expose port
EXPOSE 8005

# Run the API server
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8005"]
