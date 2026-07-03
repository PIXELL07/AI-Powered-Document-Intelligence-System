FROM python:3.11-slim

# Tesseract is a system binary, not a pip package -- required for OCR.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m spacy download en_core_web_sm

COPY . .

ENV PYTHONUNBUFFERED=1

# Railway sets $PORT; default to 8000 for local docker-compose.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
