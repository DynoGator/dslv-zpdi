# DSLV-ZPDI container (Phase 2 / mobile + Tier-1 tooling)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Core + dev deps via pyproject
COPY pyproject.toml ./
COPY requirements-dev.txt ./ 2>/dev/null || true
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential git && \
    pip install --upgrade pip && \
    pip install -e ".[dev]" && \
    apt-get purge -y build-essential && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

COPY src ./src
COPY tests ./tests
COPY tools ./tools 2>/dev/null || true
COPY *.py *.sh *.md LICENSE* README* ./ 2>/dev/null || true

# Default: run the test suite (CI friendly). Override for daemon etc.
CMD ["python", "-m", "pytest", "tests/", "-q", "--tb=short"]
