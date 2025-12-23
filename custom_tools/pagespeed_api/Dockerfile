# PageSpeed API Docker Image
# Phase 2B: Technical Scores

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pagespeed_api.py .
COPY api.py .

EXPOSE 8003

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8003"]
