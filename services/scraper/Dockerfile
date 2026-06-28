FROM python:3.11-slim

WORKDIR /app

# Install deps first for better layer caching.
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY eventscraper ./eventscraper

# Default entrypoint is overridden by docker-compose; safe fallback here.
ENTRYPOINT ["python", "-m", "eventscraper.cli"]
CMD ["--help"]
