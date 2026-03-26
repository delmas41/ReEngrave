# eclipse-temurin is multi-arch (amd64 + arm64) — works on Apple Silicon and x86
FROM eclipse-temurin:21-jdk-jammy

# Install Python 3.11, LilyPond, and utilities
RUN apt-get update && apt-get install -y \
    python3.11 python3.11-dev python3-pip \
    lilypond \
    poppler-utils \
    wget curl unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Audiveris
# The zip extracts to a versioned directory; rename it to a fixed path.
ARG AUDIVERIS_VERSION=5.3.1
RUN wget -q \
    https://github.com/Audiveris/audiveris/releases/download/${AUDIVERIS_VERSION}/Audiveris_${AUDIVERIS_VERSION}.zip \
    -O /tmp/audiveris.zip \
    && unzip -q /tmp/audiveris.zip -d /opt/ \
    && mv /opt/Audiveris* /opt/Audiveris 2>/dev/null || true \
    && rm /tmp/audiveris.zip \
    && chmod +x /opt/Audiveris/bin/Audiveris

ENV AUDIVERIS_HOME=/opt/Audiveris
ENV PATH="$AUDIVERIS_HOME/bin:$PATH"

WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
