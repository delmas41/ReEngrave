# eclipse-temurin is multi-arch (amd64 + arm64) — works on Apple Silicon and x86
FROM eclipse-temurin:21-jdk-jammy

# Install Python 3.11, LilyPond, and utilities
RUN apt-get update && apt-get install -y \
    python3.11 python3.11-dev python3-pip \
    lilypond \
    poppler-utils \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 \
    wget curl unzip git \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Install Audiveris (best-effort — app still runs without it)
# PDF OMR will return an error if Audiveris is unavailable.
# Tag v5.4 is the latest stable release.
# ---------------------------------------------------------------------------
ARG AUDIVERIS_TAG=v5.4
RUN ( \
    git clone --depth 1 --branch ${AUDIVERIS_TAG} \
        https://github.com/Audiveris/audiveris.git /tmp/audiveris \
    && cd /tmp/audiveris \
    && chmod +x gradlew \
    && ./gradlew assemble --no-daemon \
    && DIST=$(find /tmp/audiveris -name "*.zip" -path "*/distributions/*" | head -1) \
    && [ -n "$DIST" ] \
    && unzip -q "$DIST" -d /opt/ \
    && mv /opt/app-* /opt/Audiveris 2>/dev/null || mv /opt/Audiveris-* /opt/Audiveris 2>/dev/null || true \
    && chmod +x /opt/Audiveris/bin/Audiveris \
    && rm -rf /tmp/audiveris ~/.gradle \
    && echo "✓ Audiveris ${AUDIVERIS_TAG} installed" \
) || echo "⚠ Audiveris build skipped — PDF OMR unavailable (MusicXML upload still works)"

ENV AUDIVERIS_HOME=/opt/Audiveris
ENV PATH="$AUDIVERIS_HOME/bin:$PATH"

# ---------------------------------------------------------------------------
# Python application
# ---------------------------------------------------------------------------
WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
