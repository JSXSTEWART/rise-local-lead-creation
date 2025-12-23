# BBB Scraper Docker Image
# Phase 2E: Reputation Analysis

FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install chromium

COPY bbb_scraper.py .
COPY api.py .

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8002"]
