# Stage 1: build conda env with micromamba
FROM mambaorg/micromamba:1.5.8-jammy AS builder

COPY environment.yml /tmp/environment.yml
RUN micromamba create -y -n energieapp -f /tmp/environment.yml \
 && micromamba clean -a -y

# Stage 2: final image
FROM mambaorg/micromamba:1.5.8-jammy

# Install ODBC driver & dependencies as root
USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      curl apt-transport-https gnupg \
 && curl -sSL https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
 && curl -sSL https://packages.microsoft.com/config/ubuntu/22.04/prod.list \
       -o /etc/apt/sources.list.d/mssql-release.list \
 && apt-get update \
 && ACCEPT_EULA=Y DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      msodbcsql17 unixodbc-dev \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Bring in the conda environment
COPY --from=builder /opt/conda/envs/energieapp /opt/conda/envs/energieapp

# Copy the app, remove .sql, and make run_app.sh executable—all as root
WORKDIR /opt/app
COPY . /opt/app
RUN find /opt/app -type f -name "*.sql" -delete \
 && chmod +x run_app.sh

# Expose default UI port
EXPOSE 8868

# Switch to non-root user for runtime
USER 1000

# Ensure the new conda env and app path are on PATH
ENV PATH="/opt/conda/envs/energieapp/bin:${PATH}" \
    PYTHONPATH="/opt/app:${PYTHONPATH}"

ENTRYPOINT ["bash", "/opt/app/run_app.sh"]
