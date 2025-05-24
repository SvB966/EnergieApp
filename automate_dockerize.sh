#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------------------------
# automate_dockerize.sh
# A single script to:
#   1. Create/switch to 'dockerize' branch
#   2. Generate Dockerfile & run_app.sh
#   3. Build & run the EnergieApp container
#   4. Verify the dashboard is up
#   5. Commit & push to trigger CI
# ------------------------------------------------------------------------------

# 0. Prerequisites check
: "${DB_URL:?Environment variable DB_URL must be set (e.g. export DB_URL=\"mssql+pyodbc://user:pass@host/db?driver=ODBC+Driver+17+for+SQL+Server\")}"
: "${GITHUB_USER:?Environment variable GITHUB_USER must be set to your GH username (e.g. export GITHUB_USER=SVB966)}"

echo "[1/7] Creating and switching to branch 'dockerize'..."
git fetch origin
if git show-ref --verify --quiet refs/heads/dockerize; then
  git checkout dockerize
else
  git checkout -b dockerize
fi

echo "[2/7] Writing Dockerfile..."
cat > Dockerfile << 'EOF'
# Stage 1: build conda env with micromamba
FROM mambaorg/micromamba:1.5.8-jammy AS builder
COPY environment.yml /tmp/environment.yml
RUN micromamba create -y -n energieapp -f /tmp/environment.yml && \
    micromamba clean -a -y

# Stage 2: final image
FROM mambaorg/micromamba:1.5.8-jammy
RUN apt-get update && apt-get install -y curl apt-transport-https gnupg && \
    curl -sSL https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl -sSL https://packages.microsoft.com/config/ubuntu/22.04/prod.list \
      -o /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && ACCEPT_EULA=Y DEBIAN_FRONTEND=noninteractive \
      apt-get install -y msodbcsql17 unixodbc-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
COPY --from=builder /opt/conda/envs/energieapp /opt/conda/envs/energieapp
WORKDIR /opt/app
COPY . /opt/app
RUN find /opt/app -type f -name "*.sql" -delete && \
    chmod +x run_app.sh
ENV PYTHONPATH="/opt/app:$PYTHONPATH" \
    PATH="/opt/conda/envs/energieapp/bin:$PATH"
ENTRYPOINT ["bash","/opt/app/run_app.sh"]
EOF

echo "[3/7] Writing run_app.sh..."
cat > run_app.sh << 'EOF'
#!/usr/bin/env bash
set -euo pipefail
APP_DIR="$(cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd)"
cd "$APP_DIR"
ENV_NAME="energieapp"
UI_PORT=8868
declare -A NOTEBOOK_PORTS=(
  [001_All_Types.ipynb]=8866
  [002_Data_export.ipynb]=8867
  [003_VMNED_Data_Export.ipynb]=8869
  [004_Factorupdate.ipynb]=8870
  [005_MV_Switch.ipynb]=8871
  [006_Vervanging_Tool.ipynb]=8872
  [007_Storage_Method.ipynb]=8873
  [000_Start_UI.ipynb]=$UI_PORT
)
echo "[DEBUG] Checking notebooks..."
for nb in "${!NOTEBOOK_PORTS[@]}"; do
  [[ -f "$nb" ]] || { echo "[ERROR] Missing $nb"; exit 1; }
done
echo "[DEBUG] Activating $ENV_NAME..."
micromamba activate "$ENV_NAME"
echo "[INFO] Launching Voila..."
mkdir -p logs
for nb in "${!NOTEBOOK_PORTS[@]}"; do
  port=${NOTEBOOK_PORTS[$nb]}
  name="${nb%.ipynb}"
  nohup voila "$nb" --port="$port" --no-browser --ip="0.0.0.0" \
    > "logs/${name}.log" 2>&1 &
done
echo "[DEBUG] Waiting for UI..."
while ! nc -z localhost $UI_PORT; do sleep 2; done
echo "[INFO] UI up at http://localhost:$UI_PORT"
wait
EOF
chmod +x run_app.sh

echo "[4/7] Building Docker image..."
docker build -t "${GITHUB_USER}/energieapp:local" --build-arg REV="$(git rev-parse HEAD)" .

echo "[5/7] Running Docker container..."
docker run -d \
  --name energieapp_local \
  -p 8868:8868 \
  -e DB_URL="$DB_URL" \
  -v "$PWD/data":/opt/app/data \
  "${GITHUB_USER}/energieapp:local"

echo "[6/7] Verifying container startup..."
until curl -sSf http://localhost:8868 > /dev/null; do
  printf "."
  sleep 2
done
echo -e "\n[INFO] Dashboard is live at http://localhost:8868"

echo "[7/7] Committing & pushing..."
git add Dockerfile run_app.sh
git commit -m "chore: add Dockerfile & run_app.sh for containerization"
git push -u origin dockerize

echo "[DONE] All steps completed. The GitHub Actions workflow will run on push."
