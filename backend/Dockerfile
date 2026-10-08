# Slim Python base. The OMR pipeline (ultralytics + torch CPU) is the
# main heavyweight dependency now — Audiveris (which needed a full JDK)
# was retired in favour of the in-house tools/omr pipeline.
FROM python:3.11-slim-bookworm

# ---------------------------------------------------------------------------
# System dependencies
#
#   lilypond, poppler-utils       — score engraving + PDF rasterization
#   cairo / pango / gdk-pixbuf    — cairosvg runtime (Verovio SVG → PNG)
#   libgl1, libglib2.0-0          — opencv-python-headless runtime libs
#   libsm6, libxext6, libxrender1 — opencv runtime libs
#   curl                          — healthcheck + ad-hoc debugging
#   git                           — kept so musicxml2ly / pip install -e work
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    lilypond \
    poppler-utils \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
    curl git \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Python application
#
# The build context is the repo root (see docker-compose.yml) so both
# backend/ and tools/ can be copied into the image. The OMR weights file
# is intentionally NOT baked in — it's mounted as a volume at
# /app/tools/omr/training/data/weights/ by docker-compose.
# ---------------------------------------------------------------------------
WORKDIR /app

# Install Python deps first so changes elsewhere don't bust the layer cache.
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Backend source goes at /app/ (preserves the existing import layout —
# `from core.config import settings`, `from modules import ...`).
COPY backend/ .

# OMR pipeline source goes at /app/tools/ so `from tools.omr.transcribe
# import transcribe` works.
COPY tools/ ./tools/

# The repo-root build context ignores backend/.dockerignore (Docker reads the
# ignore file at the context root), so drop the test suite explicitly too.
RUN rm -rf /app/tests

# ---------------------------------------------------------------------------
# Run as a non-root user. uploads/, exports/ and data/ are the three named
# volumes docker-compose mounts; they must be writable by this user. HOME is
# set because ultralytics/matplotlib write config and cache under it.
#
# NOTE for existing deployments: a named volume created by the previous
# (root) image stays root-owned -- docker only copies image ownership into a
# NEW, empty volume. Fix once with:
#   docker compose run --rm --user root backend chown -R app:app /app/uploads /app/exports /app/data
# ---------------------------------------------------------------------------
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --create-home --home-dir /home/app app \
    && mkdir -p /app/uploads /app/exports /app/data \
    && chown -R app:app /app/uploads /app/exports /app/data /home/app
ENV HOME=/home/app PYTHONDONTWRITEBYTECODE=1
USER app

EXPOSE 8000
# --proxy-headers / --forwarded-allow-ips='*': the rate limiter and the logs
# must see the real client IP from X-Forwarded-For, not nginx's. '*' is right
# ONLY because the backend publishes no port in docker-compose.prod.yml, so
# the sole peer that can reach it is the frontend nginx, which sets
# X-Forwarded-For. (docker-compose.yml, dev, publishes 8000: there a client can
# spoof the header, which is acceptable for local development only.)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
