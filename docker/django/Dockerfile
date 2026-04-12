# Official Playwright image (Ubuntu Jammy) — already includes all browser deps
FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

# Extra system deps needed for psycopg2 and pdfplumber
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    gettext \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Browsers already installed in the base image; just verify
RUN playwright install chromium

COPY . .

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
