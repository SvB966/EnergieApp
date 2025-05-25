@echo off
setlocal EnableDelayedExpansion

echo ================================================================
echo [INFO] ENERGYMONITOR - Alles in 1x starten
echo ================================================================

REM
REM
cd /d %~dp0
echo [DEBUG] Huidige directory: %cd%

REM ----------------------------------------------------------------
REM
if not exist "001_All_Types.ipynb" (
    echo [ERROR] Bestand "001_All_Types.ipynb" niet gevonden.
    pause
    exit /b 1
)
if not exist "002_Data_export.ipynb" (
    echo [ERROR] Bestand "002_Data_export.ipynb" niet gevonden.
    pause
    exit /b 1
)
if not exist "003_VMNED_Data_Export.ipynb" (
    echo [ERROR] Bestand "003_VMNED_Data_Export.ipynb" niet gevonden.
    pause
    exit /b 1
)
if not exist "004_Factorupdate.ipynb" (
    echo [ERROR] Bestand "004_Factorupdate.ipynb" niet gevonden.
    pause
    exit /b 1
)

if not exist "005_MV_Switch.ipynb" (
    echo [ERROR] Bestand "005_MV_Switch.ipynb" niet gevonden.
    pause
    exit /b 1
)

if not exist "006_Vervanging_Tool.ipynb" (
    echo [ERROR] Bestand "006_Vervanging_Tool.ipynb" niet gevonden.
    pause
    exit /b 1
)

if not exist "007_Storage_Method.ipynb" (
    echo [ERROR] Bestand "007_Storage_Method.ipynb" niet gevonden.
    pause
    exit /b 1
)

if not exist "000_Start_UI.ipynb" (
    echo [ERROR] Bestand "000_Start_UI.ipynb" niet gevonden.
    pause
    exit /b 1
)

echo [DEBUG] Alle vereiste notebooks gevonden.

REM 
REM
where conda >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [INFO] Conda niet gevonden in PATH.
    IF EXIST "%UserProfile%\Miniconda3\Scripts\conda.exe" (
        echo [INFO] Miniconda al aanwezig. Voeg Scripts toe aan PATH.
        set "PATH=%UserProfile%\Miniconda3\Scripts;%PATH%"
    ) ELSE (
        IF EXIST "%UserProfile%\Miniconda3" (
            echo [INFO] Miniconda-directory gevonden. Voeg Scripts toe aan PATH.
            set "PATH=%UserProfile%\Miniconda3\Scripts;%PATH%"
        ) ELSE (
            echo [INFO] Conda wordt nu automatisch geïnstalleerd...
            curl https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe -o miniconda.exe
            start /wait "" miniconda.exe /S /D=%UserProfile%\Miniconda3
            del miniconda.exe
            set "PATH=%UserProfile%\Miniconda3\Scripts;%PATH%"
        )
    )
    IF NOT EXIST "%UserProfile%\Miniconda3\Scripts\conda.exe" (
        echo [ERROR] Automatische installatie van Conda is mislukt.
        pause
        exit /b 1
    ) ELSE (
        echo [INFO] Conda is nu beschikbaar.
    )
) ELSE (
    echo [DEBUG] Conda is beschikbaar.
)

REM
REM
echo [DEBUG] Controleren of de environment "energymonitor_env" bestaat...
"%UserProfile%\Miniconda3\Scripts\conda.exe" env list | findstr /I "energymonitor_env" >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [INFO] Environment "energymonitor_env" niet gevonden. Wordt aangemaakt...
    "%UserProfile%\Miniconda3\Scripts\conda.exe" env create -f environment.yml
    set "envfound="
    for /f "delims=" %%a in ('"%UserProfile%\Miniconda3\Scripts\conda.exe" env list') do (
        echo %%a | findstr /I "energymonitor_env" >nul && set "envfound=1"
    )
    IF defined envfound (
        echo [INFO] Environment "energymonitor_env" succesvol aangemaakt.
    ) ELSE (
        echo [ERROR] Aanmaken van environment "energymonitor_env" mislukt.
        pause
        exit /b 1
    )
) ELSE (
    echo [DEBUG] Environment "energymonitor_env" bestaat.
    "%UserProfile%\Miniconda3\Scripts\conda.exe" list -n energymonitor_env xlsxwriter | findstr /I "xlsxwriter" >nul 2>&1
    IF %ERRORLEVEL% NEQ 0 (
        echo [DEBUG] xlsxwriter niet gevonden. Environment update wordt uitgevoerd...
        "%UserProfile%\Miniconda3\Scripts\conda.exe" env update -n energymonitor_env -f environment.yml --prune
        IF %ERRORLEVEL% NEQ 0 (
            echo [ERROR] Update van environment "energymonitor_env" mislukt.
            pause
            exit /b 1
        ) ELSE (
            echo [INFO] Environment "energymonitor_env" succesvol geüpdatet.
        )
    ) ELSE (
        echo [DEBUG] xlsxwriter is aanwezig in de environment.
    )
)

REM ----------------------------------------------------------------
REM 5. Activeer de environment "energymonitor_env" in deze shell
echo [DEBUG] Activeren van environment "energymonitor_env"...
call "%UserProfile%\Miniconda3\Scripts\activate.bat" energymonitor_env
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Kon de environment "energymonitor_env" niet activeren.
    pause
    exit /b 1
) ELSE (
    echo [DEBUG] Environment "energymonitor_env" succesvol geactiveerd.
)

REM ----------------------------------------------------------------
REM 6. Start alle notebooks in aparte vensters

echo [INFO] Start Energiemonitor (poort 8866)...
start "" /min cmd /c "conda run -n energymonitor_env voila 001_All_Types.ipynb --port=8866 --no-browser --ip=127.0.0.1"

echo [INFO] Start Data Export (poort 8867)...
start "" /min cmd /c "conda run -n energymonitor_env voila 002_Data_export.ipynb --port=8867 --no-browser --ip=127.0.0.1"

echo [INFO] Start VMNED Data Export (poort 8869)...
start "" /min cmd /c "conda run -n energymonitor_env voila 003_VMNED_Data_Export.ipynb --port=8869 --no-browser --ip=127.0.0.1"

echo [INFO] Start Factorupdate (poort 8870)...
start "" /min cmd /c "conda run -n energymonitor_env voila 004_Factorupdate.ipynb --port=8870 --no-browser --ip=127.0.0.1"

echo [INFO] Start MV Switch (005_MV_Switch.ipynb) (poort 8871)...
start "" /min cmd /c "conda run -n energymonitor_env voila 005_MV_Switch.ipynb --port=8871 --no-browser --ip=127.0.0.1"

echo [INFO] Start Vervanging Tool (006_Vervanging_Tool.ipynb) (poort 8872)...
start "" /min cmd /c "conda run -n energymonitor_env voila 006_Vervanging_Tool.ipynb --port=8872 --no-browser --ip=127.0.0.1"

echo [INFO] Storage method Tool (007_Storage_Method.ipynb) (poort 8873)...
start "" /min cmd /c "conda run -n energymonitor_env voila 007_Storage_Method.ipynb --port=8873 --no-browser --ip=127.0.0.1"

echo [INFO] Start Start_UI (poort 8868)...
start "" /min cmd /c "conda run -n energymonitor_env voila 000_Start_UI.ipynb --port=8868 --no-browser --ip=127.0.0.1"

REM ----------------------------------------------------------------
REM 7. Wacht tot het Start_UI-notebook op poort 8868 draait
:WaitForUI
powershell -Command "try { if ((Test-NetConnection -ComputerName 127.0.0.1 -Port 8868).TcpTestSucceeded) { exit 0 } else { exit 1 } } catch { exit 1 }"
IF %ERRORLEVEL% NEQ 0 (
    echo [DEBUG] Wachten tot 000_Start_UI op poort 8868 actief is...
    timeout /t 2 /nobreak >nul
    goto WaitForUI
)

echo [INFO] Start_UI is actief op poort 8868!
echo [INFO] De browser wordt nu geopend op http://127.0.0.1:8868...
start "" "http://127.0.0.1:8868"

echo ================================================================
echo [INFO] Alle applicaties zijn gestart.
echo [INFO] Dit venster kan open blijven of worden afgesloten.
echo ================================================================

pause
exit /b 0
