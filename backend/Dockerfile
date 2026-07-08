FROM python:3.12-slim AS builder

WORKDIR /src

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m pip install --upgrade pip setuptools wheel && \
    python -m pip install --no-cache-dir --prefix /install -r requirements.txt

FROM python:3.12-slim
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Create app user and directories
RUN useradd -m -u 1000 appuser && mkdir -p /app/uploads /app/backups /app/logs && chown -R appuser:appuser /app

# Copy app
COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8000

ENV UVICORN_WORKERS=1

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
