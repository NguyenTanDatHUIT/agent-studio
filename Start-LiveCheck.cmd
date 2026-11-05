@echo off
setlocal
cd /d "%~dp0"
set "studioPython=%~dp0.venv\Scripts\python.exe"
if not exist "%studioPython%" set "studioPython=%~dp0.runtime\python\python.exe"
if not exist "%studioPython%" (
    echo Python runtime missing. See docs/LIVE-RUN.md for manual setup.
    exit /b 2
)
echo REAL MODEL CHECK: uses your CLI login and may consume quota.
echo Target: isolated calculator repository in .local-run\live-check\repo.
"%studioPython%" -m tools.prepare_live_check --enqueue
if errorlevel 1 exit /b %errorlevel%
call "%~dp0Start-AgentStudio.cmd" "%~dp0.local-run\live-check\owner.json"
