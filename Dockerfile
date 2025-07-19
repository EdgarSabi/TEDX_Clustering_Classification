# Build stage voor basis dependencies
FROM python:3.11-slim as builder-base

# Installeer build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
        libpq-dev \
        git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Installeer basis requirements
COPY requirements-build.txt .
RUN pip install --no-cache-dir -r requirements-build.txt && \
    rm -rf ~/.cache/pip/*

# Build stage voor ML dependencies
FROM builder-base as builder-ml

# Installeer ML requirements
COPY requirements-ml.txt .
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.2.0+cpu && \
    pip install --no-cache-dir -r requirements-ml.txt && \
    pip cache purge && \
    rm -rf ~/.cache/pip/*

# Model optimization stage
FROM builder-ml as model-optimizer
COPY models/*.joblib ./models/
RUN python -c "import joblib, os; \
    [joblib.dump(joblib.load(f'models/{f}'), f'models/optimized_{f}', compress=9) \
    for f in os.listdir('models') if f.endswith('.joblib')]"

# Final stage
FROM python:3.11-slim

# Installeer runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        libpq5 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Kopieer virtual environment
COPY --from=builder-ml /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /s1146363

# Kopieer alleen benodigde files
COPY main.py logger.py setup_connections.py get_video_data.py setup_database.py classification.py clusteranalysis.py ./

# Kopieer geoptimaliseerde models
COPY --from=model-optimizer models/optimized_*.joblib ./models/

# Maak downloads directory
RUN mkdir -p downloads

CMD ["python3", "-u", "main.py"]