# Screenshot Service Docker Image
# Phase 2A: Visual Analysis

FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install chromium

COPY screenshot_service.py .
COPY api.py .

EXPOSE 8004

# Optional: Set Gemini API key for vision analysis
ENV GOOGLE_GEMINI_API_KEY=""

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8004/health || exit 1

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8004"]
