###############################################################################
# EnergieApp – multi-stage Docker build (micromamba, src-layout, Voila)
###############################################################################

############################
# Stage 1 – build Conda env
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

# need root for apt
USER root

# ---- OS packages (ODBC 17 + netcat) ----------------------------------------
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
    apt-get clean -y && rm -rf /var/lib/apt/lists/*

# ---- Conda env -------------------------------------------------------------
COPY --from=builder /opt/conda/envs/energieapp /opt/conda/envs/energieapp

# ---- App source ------------------------------------------------------------
WORKDIR /opt/app
COPY . /opt/app
RUN find /opt/app -type f -name '*.sql' -delete \
 && chmod +x /opt/app/bin/run_app.sh

# runtime dirs for unprivileged user
RUN mkdir -p /opt/app/.local/share /opt/app/.config /opt/app/.runtime \
 && chown -R 1000:1000 /opt/app
USER 1000

# ---- Runtime environment ---------------------------------------------------
ENV PATH="/opt/conda/envs/energieapp/bin:$PATH" \
    PYTHONPATH="/opt/app/src:$PYTHONPATH" \
    PORT=8868

EXPOSE 8868
ENTRYPOINT ["/bin/bash", "/opt/app/bin/run_app.sh"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
  CMD nc -z 127.0.0.1 8868 || exit 1
