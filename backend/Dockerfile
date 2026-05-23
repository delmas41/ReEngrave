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

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
