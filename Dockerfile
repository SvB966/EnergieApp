# EnergieApp container
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update \ 
    && apt-get install -y --no-install-recommends \
        build-essential \
        unixodbc-dev \
        curl \
        netcat \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . ./

CMD ["./run_app.sh"]
