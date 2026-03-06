# ---------- BOT BASE ----------
FROM python:3.12-slim AS bot-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /opt/bot

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade --no-cache-dir uv certifi

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

COPY alembic.ini .
COPY ./app ./app

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

FROM bot-base AS bot
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uv", "run", "python", "-m", "app.main"]


# ---------- WORKER BASE (Playwright) ----------
FROM mcr.microsoft.com/playwright/python:v1.58.0-noble AS worker-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /opt/bot

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

COPY ./app ./app

FROM worker-base AS worker
CMD ["uv", "run", "python", "-m", "app.workers.product_add_worker"]
