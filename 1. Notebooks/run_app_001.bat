@echo off
setlocal EnableDelayedExpansion
rem ================================================================
rem  ENERGYMONITOR – alles in één keer installeren & starten
rem ================================================================

rem -----------------------------------------------------------------
rem 0.  Naar map van dit script
cd /d "%~dp0"
echo [DEBUG] Huidige directory: %cd%

rem -----------------------------------------------------------------
rem 1.  Vereiste notebooks controleren
for %%N in (
    001_All_Types.ipynb
    002_Data_export.ipynb
    003_VMNED_Data_Export.ipynb
    004_Factorupdate.ipynb
    005_MV_Switch.ipynb
    006_Vervanging_Tool.ipynb
    007_Storage_Method.ipynb
    000_Start_UI.ipynb
) do (
    if not exist "%%N" (
        echo [ERROR] Bestand "%%N" niet gevonden.
        pause & exit /b 1
    )
)
echo [DEBUG] Alle vereiste notebooks zijn gevonden.

rem -----------------------------------------------------------------
rem 2.  Conda opsporen of installeren
where conda >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [INFO] Conda niet in PATH gevonden.
    if exist "%UserProfile%\Miniconda3\Scripts\conda.exe" (
        echo [INFO] Miniconda reeds aanwezig – voeg toe aan PATH.
        set "PATH=%UserProfile%\Miniconda3\Scripts;%PATH%"
    ) else (
        echo [INFO] Miniconda wordt nu geïnstalleerd...
        curl -L -o miniconda.exe ^
            https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe
        start /wait "" miniconda.exe /S /D=%UserProfile%\Miniconda3
        del miniconda.exe
        set "PATH=%UserProfile%\Miniconda3\Scripts;%PATH%"
    )
    if not exist "%UserProfile%\Miniconda3\Scripts\conda.exe" (
        echo [ERROR] Installatie van Conda mislukt.
        pause & exit /b 1
    )
)
set "CONDA_EXE=%UserProfile%\Miniconda3\Scripts\conda.exe"
echo [DEBUG] Conda gevonden: %CONDA_EXE%
"%CONDA_EXE%" --version

rem -----------------------------------------------------------------
rem 3.  Environment synchroon met environment.yml houden
echo [DEBUG] Controleren of environment "energymonitor_env" bestaat...
"%CONDA_EXE%" env list | findstr /I "energymonitor_env" >nul
if %ERRORLEVEL% neq 0 (
    echo [INFO] Environment wordt aangemaakt via environment.yml
    "%CONDA_EXE%" env create -f "%~dp0environment.yml" -y
) else (
    echo [INFO] Environment bestaat – uitvoeren: env update --prune
    "%CONDA_EXE%" env update -n energymonitor_env -f "%~dp0environment.yml" --prune -y
)
if %ERRORLEVEL% neq 0 (
    echo [ERROR] (Aan)maken of updaten van de environment is mislukt.
    pause & exit /b 1
)

rem -----------------------------------------------------------------
rem 4.  Environment activeren
echo [DEBUG] Activeren van environment...
call "%UserProfile%\Miniconda3\Scripts\activate.bat" energymonitor_env
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Kon environment niet activeren.
    pause & exit /b 1
)
echo [DEBUG] Environment geactiveerd.

rem -----------------------------------------------------------------
rem 5.  Verificatie: alle dependencies aanwezig?
echo [INFO] Scannen van environment op ontbrekende packages...
python "%~dp0\verify_env_deps.py" "%~dp0environment.yml" energymonitor_env
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Dependency-scan faalde – zie meldingen hierboven.
    pause & exit /b 1
)
echo [DEBUG] Alle packages aanwezig.

rem -----------------------------------------------------------------
rem 6.  Notebooks/voilà-servers starten
echo [INFO] Start notebooks (voilà) in geminimaliseerde vensters...

start "" /min cmd /c "conda run -n energymonitor_env voila 001_All_Types.ipynb        --port=8866 --no-browser --ip=127.0.0.1"
start "" /min cmd /c "conda run -n energymonitor_env voila 002_Data_export.ipynb      --port=8867 --no-browser --ip=127.0.0.1"
start "" /min cmd /c "conda run -n energymonitor_env voila 003_VMNED_Data_Export.ipynb --port=8869 --no-browser --ip=127.0.0.1"
start "" /min cmd /c "conda run -n energymonitor_env voila 004_Factorupdate.ipynb     --port=8870 --no-browser --ip=127.0.0.1"
start "" /min cmd /c "conda run -n energymonitor_env voila 005_MV_Switch.ipynb        --port=8871 --no-browser --ip=127.0.0.1"
start "" /min cmd /c "conda run -n energymonitor_env voila 006_Vervanging_Tool.ipynb  --port=8872 --no-browser --ip=127.0.0.1"
start "" /min cmd /c "conda run -n energymonitor_env voila 007_Storage_Method.ipynb   --port=8873 --no-browser --ip=127.0.0.1"
start "" /min cmd /c "conda run -n energymonitor_env voila 000_Start_UI.ipynb         --port=8868 --no-browser --ip=127.0.0.1"

rem -----------------------------------------------------------------
rem 7.  Wachten tot hoofd-UI online is
:WAIT
powershell -Command ^
  "try {if ((Test-NetConnection 127.0.0.1 -Port 8868).TcpTestSucceeded) {exit 0} else {exit 1}} catch {exit 1}"
if %ERRORLEVEL% neq 0 (
    timeout /t 2 /nobreak >nul
    goto WAIT
)
echo [INFO] Hoofd-UI actief – browser wordt geopend...
start "" "http://127.0.0.1:8868"

echo ================================================================
echo [INFO] Alle applicaties zijn gestart. Dit venster mag open blijven.
echo ================================================================
pause
exit /b 0
