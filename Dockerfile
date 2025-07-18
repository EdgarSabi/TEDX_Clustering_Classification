#FROM python:3.11
#
#WORKDIR /s1146363
#
## Install FFmpeg
#RUN apt-get update && \
#    apt-get install -y ffmpeg && \
#    apt-get clean && \
#    rm -rf /var/lib/apt/lists/*
#
#COPY requirements.txt .
#
#RUN pip install -r requirements.txt
#
#COPY . .
#
#CMD ["python3", "main.py"]

# STAGE 1: Builder
FROM python:3.11-slim as builder

WORKDIR /build
COPY requirements.txt .

# Installeer build tools en dependencies
RUN pip install --no-cache-dir wheel setuptools
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.txt

# STAGE 2: Final
FROM python:3.11-slim

WORKDIR /app

# Installeer ALLEEN ffmpeg runtime
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Kopieer ALLEEN de wheels die we nodig hebben
COPY --from=builder /wheels /wheels
COPY --from=builder /build/requirements.txt .

# Installeer packages en ruim op
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt && \
    rm -rf /wheels

COPY . .

CMD ["python3", "main.py"]