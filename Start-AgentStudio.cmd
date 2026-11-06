@echo off
setlocal
cd /d "%~dp0"
set "studioPython="
set "studioPrefix="
if exist ".venv\Scripts\python.exe" set "studioPython=%~dp0.venv\Scripts\python.exe"
if not defined studioPython if exist ".runtime\python\python.exe" set "studioPython=%~dp0.runtime\python\python.exe"
if not defined studioPython (
    where py.exe >nul 2>nul
    if not errorlevel 1 (
        set "studioPython=py.exe"
        set "studioPrefix=-3"
    )
)
if not defined studioPython (
    where python.exe >nul 2>nul
    if not errorlevel 1 set "studioPython=python.exe"
)
if not defined studioPython (
    echo Python 3.11+ is required. Install Python or use an existing virtual environment.
    pause
    exit /b 2
)
if "%~1"=="" (
    echo OFFLINE DEMO: no model calls. Pass a config file path for a real project.
    "%studioPython%" %studioPrefix% -m agent_orchestrator web --demo --open
) else (
    "%studioPython%" %studioPrefix% -m agent_orchestrator --config "%~f1" web --run-workers --open
)
exit /b %errorlevel%
