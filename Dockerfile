# Build stage voor basis dependencies
FROM python:3.11-slim as builder-base

# Installeer build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Installeer basis requirements
COPY requirements-build.txt .
RUN pip install --no-cache-dir -r requirements-build.txt

# Build stage voor ML dependencies
FROM builder-base as builder-ml

# Installeer ML requirements
COPY requirements-ml.txt .
RUN pip install --no-cache-dir -r requirements-ml.txt && \
    find /opt/venv -type d -name "__pycache__" -exec rm -r {} + && \
    find /opt/venv -type d -name "tests" -exec rm -r {} + && \
    find /opt/venv -type d -name "test" -exec rm -r {} +

# Final stage
FROM python:3.11-slim

# Kopieer virtual environment
COPY --from=builder-ml /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Installeer runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    libpq5 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /s1146363

# Kopieer alleen benodigde files
COPY main.py ./
COPY logger.py ./
COPY setup_connections.py ./
COPY get_video_data.py ./
COPY setup_database.py ./
COPY classification.py ./
COPY clusteranalysis.py ./

# Kopieer en optimaliseer models directory
COPY models/*.joblib ./models/

# Maak downloads directory
RUN mkdir -p downloads

CMD ["python3", "-u", "main.py"]