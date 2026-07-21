# ExoDossier — read-only API + built SPA in one image.
# Serves HTTP traffic and (via `docker compose exec`) runs the nightly catalog
# refresh. The ingest/graph rebuild pulls a few extra libs (astropy for KOI
# coordinate matching) listed in requirements-ingest.txt.
# Build context = repo root.

# ---------- stage 1: build the React SPA ----------
FROM node:22-slim AS web
WORKDIR /web
RUN corepack enable && corepack prepare pnpm@10.31.0 --activate
COPY web/package.json web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY web/ ./
RUN pnpm run build          # -> /web/dist

# ---------- stage 2: python runtime ----------
FROM python:3.13-slim AS runtime
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1
# requirements-api.txt = serving surface (fastapi/uvicorn/numpy/sgp4/psycopg/mcp);
# requirements-ingest.txt = the nightly refresh extras (astropy/PyYAML/requests).
COPY requirements-api.txt requirements-ingest.txt ./
RUN pip install -r requirements-api.txt -r requirements-ingest.txt
# Source needed to SERVE (api, common) and to run the nightly REFRESH
# (identity, ingest, quality, db migrations, scripts).
COPY api/ ./api/
COPY common/ ./common/
COPY identity/ ./identity/
COPY ingest/ ./ingest/
COPY quality/ ./quality/
COPY db/ ./db/
COPY scripts/ ./scripts/
COPY pyproject.toml conftest.py ./
COPY --from=web /web/dist ./web/dist
EXPOSE 8700
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8700"]
