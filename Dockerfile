###############################################################################
# Dockerfile for EnergieApp
# - Multi-stage build, Ubuntu-based micromamba image
# - Creates Conda env “energieapp” once, then copies it into a slim run image
# - Non-root runtime, installs msodbcsql17 + unixODBC non-interactively
# - Exposes Voila dashboard on $PORT (default 8868)
###############################################################################

############################
# Stage 1 – build the Conda environment
############################
FROM mambaorg/micromamba:1.5.8-jammy AS builder

# Optional: embed Git SHA for reproducible layers
ARG REV=dev
LABEL org.opencontainers.image.revision=$REV

# Copy Conda spec and create env
COPY environment.yml /tmp/environment.yml
RUN micromamba create -y -n energieapp -f /tmp/environment.yml \
 && micromamba clean -a -y           # drop package tarballs → leaner layer


############################
# Stage 2 – final runtime image
############################
FROM mambaorg/micromamba:1.5.8-jammy

# ---- System packages --------------------------------------------------------
RUN set -eux; \
    apt-get update -qq; \
    apt-get install -y --no-install-recommends \
        curl apt-transport-https gnupg netcat-openbsd; \
    curl -sSL https://packages.microsoft.com/keys/microsoft.asc | apt-key add -; \
    curl -sSL https://packages.microsoft.com/config/ubuntu/22.04/prod.list \
        -o /etc/apt/sources.list.d/mssql-release.list; \
    apt-get update -qq; \
    ACCEPT_EULA=Y DEBIAN_FRONTEND=noninteractive \
        apt-get install -y --no-install-recommends msodbcsql17 unixodbc-dev; \
    apt-get clean -y; \
    rm -rf /var/lib/apt/lists/*

# ---- Copy Conda env from builder -------------------------------------------
COPY --from=builder /opt/conda/envs/energieapp /opt/conda/envs/energieapp

# ---- Application source -----------------------------------------------------
WORKDIR /opt/app
COPY . /opt/app
# remove stored-procedure SQL files so they don’t land inside the image
RUN find /opt/app -type f -name '*.sql' -delete \
 && chmod +x /opt/app/run_app.sh

# ---- Runtime dirs for unprivileged user -------------------------------------
RUN mkdir -p /opt/app/.local/share /opt/app/.config /opt/app/.runtime \
 && chown -R 1000:1000 /opt/app

# ---- Non-root execution -----------------------------------------------------
USER 1000

ENV PATH="/opt/conda/envs/energieapp/bin:$PATH" \
    PYTHONPATH="/opt/app:$PYTHONPATH" \
    PORT=8868                 # main UI port (override at runtime)

EXPOSE 8868
ENTRYPOINT ["/bin/bash", "/opt/app/run_app.sh"]

# ---- Liveness probe (optional) ---------------------------------------------
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
  CMD nc -z 127.0.0.1 8868 || exit 1
