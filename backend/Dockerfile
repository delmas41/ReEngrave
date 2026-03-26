FROM eclipse-temurin:21-jdk-jammy

# Install Python 3.11
RUN apt-get update && apt-get install -y \
    python3.11 python3.11-dev python3-pip \
    lilypond \
    poppler-utils \
    wget curl unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Audiveris
ARG AUDIVERIS_VERSION=5.3.1
RUN wget -q https://github.com/Audiveris/audiveris/releases/download/${AUDIVERIS_VERSION}/Audiveris_${AUDIVERIS_VERSION}.zip \
    -O /tmp/audiveris.zip \
    && unzip /tmp/audiveris.zip -d /opt/ \
    && rm /tmp/audiveris.zip

ENV AUDIVERIS_HOME=/opt/Audiveris
ENV PATH="$AUDIVERIS_HOME/bin:$PATH"

WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
