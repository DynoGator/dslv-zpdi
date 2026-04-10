# DSLV-ZPDI Reproducible Development Environment
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for hardware drivers (SDR/Serial)
RUN apt-get update && apt-get install -p -y \
    librtlsdr-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Set environment for virtual validation
ENV DEV_SIMULATOR=1
ENV PYTHONPATH=/app

# Default command: run the regression suite
CMD ["python", "tests/test_pipeline.py"]
