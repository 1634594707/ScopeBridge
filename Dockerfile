# ScopeBridge in one image: the API and the built SPA, served from one origin.
#
#   docker build -t scopebridge .
#   docker run --rm -p 8000:8000 \
#     -e DATABASE_URL=postgresql+psycopg://user:pass@host:5432/scopebridge \
#     -e SESSION_SECRET=... -e SELLER_PASSWORD=... -e CLIENT_PASSWORD=... \
#     scopebridge
#
# `docker compose --profile app up -d --build` runs this next to the database.

# --- frontend ---------------------------------------------------------------
FROM node:22-alpine AS frontend
RUN npm install --global pnpm@10
WORKDIR /build
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

# --- runtime ----------------------------------------------------------------
FROM python:3.12-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv:0.10.10 /uv /usr/local/bin/uv

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Dependencies first: they change far less often than the source.
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/ ./
COPY --from=frontend /build/dist ./static

RUN chmod +x docker-entrypoint.sh \
    && useradd --system --uid 10001 scopebridge \
    && chown -R scopebridge /app
USER scopebridge

EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]
