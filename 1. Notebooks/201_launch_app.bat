@echo off
setlocal

REM Dynamisch pad naar de Miniconda-installatie in de user-home
set "CONDA_PATH=%USERPROFILE%\Miniconda3"

REM 
echo [DEBUG] Changing to the script directory...
cd /d "%~dp0"

echo [DEBUG] Activating environment energymonitor_env...
call "%CONDA_PATH%\Scripts\activate.bat" energymonitor_env
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Could not activate environment 'energymonitor_env'.
    pause
    exit /b 1
)

echo [DEBUG] Environment activated. Now running launch_app.py...
python 202_launch_app.py
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] 202_launch_app.py encountered an error.
    pause
    exit /b 1
)
echo [INFO] Done. Press any key to close...
pause
exit /b 0
