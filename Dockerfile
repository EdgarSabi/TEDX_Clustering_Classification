FROM python:3.11-slim AS builder-base

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
        libpq-dev \
        git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN python -m pip install --upgrade pip setuptools wheel

COPY requirements-build.txt .
RUN pip install --no-cache-dir -r requirements-build.txt && \
    rm -rf ~/.cache/pip/*

FROM builder-base AS builder-ml

COPY requirements-ml.txt .

RUN pip install --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cpu \
    torch==2.2.0+cpu

RUN pip install --no-cache-dir --no-build-isolation -r requirements-ml.txt && \
    pip cache purge && \
    rm -rf ~/.cache/pip/*

FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        libpq5 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder-ml /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /s1146363

COPY main.py logger.py setup_connections.py get_video_data.py setup_database.py classification.py clusteranalysis.py ./
COPY models/ ./models/

RUN mkdir -p downloads

CMD ["python3", "-u", "main.py"]
