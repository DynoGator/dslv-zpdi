FROM python:3.14-slim@sha256:44dd04494ee8f3b538294360e7c4b3acb87c8268e4d0a4828a6500b1eff50061

WORKDIR /app

# System dependencies needed by current repo dependency surface
RUN apt-get update && apt-get install -y --no-install-recommends \
    libhackrf-dev \
    soapysdr-module-hackrf \
    libiio-dev \
    libad9361-dev \
    libusb-1.0-0-dev \
    pkg-config \
    git \
    libhdf5-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project
COPY . .

# Simulator mode for non-hardware environments
ENV DEV_SIMULATOR=1

# Install the package the same way the installer validates it
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -e '.[dev]'
RUN python -m pip check

# Validation contract
RUN pytest -q tests
RUN python tools/orphan_checker.py
RUN python tools/check_version_sync.py
RUN python tools/repo_guard.py

RUN useradd --create-home --shell /usr/sbin/nologin dslv \
    && chown -R dslv:dslv /app
USER dslv

CMD ["pytest", "-q", "tests"]
