FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Install system deps for pypdf/docx/text processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libxml2-dev libxslt1-dev \
    libzip-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Ensure uploads folder exists (persisted via volume at runtime)
RUN mkdir -p /app/uploads

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser || true
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

# Use Gunicorn for production
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000", "--workers", "4"]
