# ── Stage 1: Builder ──
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Runtime ──
FROM python:3.11-slim

# Dependencias runtime de PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl && \
    rm -rf /var/lib/apt/lists/*

# Usuario no-root
RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app

# Copiar dependencias del builder
COPY --from=builder /install /usr/local

# Copiar aplicacion
COPY --chown=app:app . .

USER app

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["gunicorn", "main:app", "-c", "gunicorn.conf.py"]
