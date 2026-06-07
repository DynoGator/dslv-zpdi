# DSLV-ZPDI container (Phase 2 / mobile + Tier-1 tooling)
# Robust, incorporates all new changes: pyproject.toml only, src/dslv_zpdi layout, editable install
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# [SUCCEEDED/FAILED reporting in build output]
RUN echo "[*] [Docker] Updating apt..." && apt-get update

RUN echo "[*] [Docker] Installing build deps..." && apt-get install -y --no-install-recommends \
      build-essential git && \
    echo "[SUCCEEDED] apt build deps" || (echo "[FAILED] apt build deps" ; echo "Recommended: docker build with --no-cache or check base image network"; exit 1)

# Core + dev deps via pyproject (new source of truth, no requirements.txt)
COPY pyproject.toml ./
COPY requirements-dev.txt ./ 2>/dev/null || true
RUN echo "[*] [Docker] pip upgrade + editable install (.[dev] for all new changes + layout)..." && \
    pip install --upgrade pip && \
    pip install -e ".[dev]" && \
    echo "[SUCCEEDED] pip install -e .[dev] (pyproject + src layout)" || \
    (echo "[FAILED] pip install -e .[dev]" ; echo "Recommended corrective action: Ensure pyproject.toml has [build-system] and [project]; docker build --no-cache; or inside container: apt-get install -y python3-dev ; pip install -e .[dev]"; exit 1)

RUN apt-get purge -y build-essential && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

COPY src ./src
COPY tests ./tests
COPY tools ./tools 2>/dev/null || true
COPY *.py *.sh *.md LICENSE* README* ./ 2>/dev/null || true

# Post-copy smoke
RUN echo "[*] [Docker] Smoke import new package layout..." && python -c "
import sys
sys.path.insert(0, 'src')
import dslv_zpdi
print('Version:', getattr(dslv_zpdi, '__version__', 'ok'))
print('[SUCCEEDED] Docker smoke for new layout')
" || echo "[FAILED] Docker smoke - Recommended: check COPY src and pyproject"

# Default: run the test suite (CI friendly). Override for daemon etc.
CMD ["python", "-m", "pytest", "tests/", "-q", "--tb=short"]
