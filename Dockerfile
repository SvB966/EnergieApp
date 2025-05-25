# Dockerfile
###############################################################################
# EnergieApp – multi-stage Docker build (micromamba, Voila dashboards)
###############################################################################

############################
# Stage 1 – build the Conda environment
############################
FROM mambaorg/micromamba:1.5.8-jammy AS builder

ARG REV=dev
LABEL org.opencontainers.image.revision=$REV

COPY environment.yml /tmp/environment.yml
RUN micromamba create -y -n energieapp -f /tmp/environment.yml \
 && micromamba clean -a -y

############################
# Stage 2 – runtime image
############################
FROM mambaorg/micromamba:1.5.8-jammy

# Install ODBC Driver 17 & netcat as root
USER root
RUN set -eux; \
    apt-get update -qq; \
    apt-get install -y --no-install-recommends \
      curl apt-transport-https gnupg netcat-openbsd; \
    curl -sSL https://packages.microsoft.com/keys/microsoft.asc \
      | apt-key add -; \
    curl -sSL https://packages.microsoft.com/config/ubuntu/22.04/prod.list \
      -o /etc/apt/sources.list.d/mssql-release.list; \
    apt-get update -qq; \
    ACCEPT_EULA=Y DEBIAN_FRONTEND=noninteractive \
      apt-get install -y --no-install-recommends \
        msodbcsql17 unixodbc-dev; \
    apt-get clean -y && rm -rf /var/lib/apt/lists/*

# Copy the pre-built Conda env
COPY --from=builder /opt/conda/envs/energieapp /opt/conda/envs/energieapp

# Copy all application code and notebooks
WORKDIR /opt/app
COPY . /opt/app
# Remove stored-procedure SQL files and make launcher executable
RUN find /opt/app -type f -name '*.sql' -delete \
 && chmod +x /opt/app/run_app.sh

# Prepare runtime directories & permissions for non-root user
RUN mkdir -p /opt/app/.local/share /opt/app/.config /opt/app/.runtime /opt/app/logs \
 && chown -R 1000:1000 /opt/app
USER 1000

# Runtime environment
ENV PATH="/opt/conda/envs/energieapp/bin:$PATH" \
    PYTHONPATH="/opt/app/1. Notebooks:$PYTHONPATH" \
    PORT=8868

EXPOSE 8868
ENTRYPOINT ["/bin/bash","/opt/app/run_app.sh"]

# Liveness probe for orchestrators
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
  CMD nc -z 127.0.0.1 8868 || exit 1
