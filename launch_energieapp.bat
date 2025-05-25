@echo off
REM EnergieApp launcher – Windows (native Docker or WSL engine)
CD /D "%~dp0"
SETLOCAL ENABLEDELAYEDEXPANSION

SET "COMPOSE_CMD="
docker version >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    docker compose version >nul 2>&1 && SET "COMPOSE_CMD=docker compose"
    IF NOT DEFINED COMPOSE_CMD docker-compose version >nul 2>&1 && SET "COMPOSE_CMD=docker-compose"
)

IF NOT DEFINED COMPOSE_CMD (
    wsl docker version >nul 2>&1
    IF %ERRORLEVEL% EQU 0 (
        wsl docker compose version >nul 2>&1 && SET "COMPOSE_CMD=wsl docker compose"
        IF NOT DEFINED COMPOSE_CMD wsl docker-compose version >nul 2>&1 && SET "COMPOSE_CMD=wsl docker-compose"
    )
)

IF NOT DEFINED COMPOSE_CMD (
    ECHO [ERROR] Docker CLI/daemon not found. Install or start Docker.
    PAUSE & EXIT /B 1
)

%COMPOSE_CMD% up --build -d
IF ERRORLEVEL 1 (
    ECHO [ERROR] EnergieApp failed to start.
    PAUSE & EXIT /B 1
)

ECHO [INFO] EnergieApp running at http://localhost:8868
start http://localhost:8868
EXIT /B 0
