FROM python:3.11-slim AS builder
WORKDIR /install
COPY requirements.txt .
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc \
    && pip install --prefix=/install -r requirements.txt \
    && apt-get purge -y build-essential gcc \
    && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

FROM python:3.11-slim AS runtime
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY --from=builder /install /usr/local
COPY run_app.sh /app/run_app.sh
COPY '1. Notebooks' /app/notebooks
RUN chmod +x /app/run_app.sh
EXPOSE 8866 8867 8868 8869 8870 8871 8872 8873
CMD ["/app/run_app.sh"]
