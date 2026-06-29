FROM python:3.12-slim

# Pillow needs zlib/libjpeg at runtime; build tools are only needed transiently
# for any packages that have no wheel for the target platform.
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        libjpeg62-turbo \
        zlib1g \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY config ./config
COPY assets ./assets

# Mounted as volumes in docker-compose; created here so the app can write to
# them even if no volume is attached (e.g. local `docker run`).
RUN mkdir -p /data /app/logs

ENV DB_PATH=/data/app.db \
    TEMPLATES_DIR=/app/config/templates \
    LOG_DIR=/app/logs \
    FONTAWESOME_FONT_PATH=/app/assets/fontawesome/fa-solid-900.ttf \
    FONTAWESOME_MAP_PATH=/app/assets/fontawesome/icon-map.json \
    CUSTOM_ICONS_DIR=/app/assets/icons

EXPOSE 8000

# Basic liveness/readiness check - /health requires no API key.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
