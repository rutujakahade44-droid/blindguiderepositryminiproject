@echo off
title VisionMate AI — Startup
color 0B
echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║         VisionMate AI — Starting Up          ║
echo  ║     AI-Powered Visual Assistance System      ║
echo  ╚══════════════════════════════════════════════╝
echo.

REM ── Try finding Python in embeddable folder first
set PYEXE=
if exist "%~dp0python311\python.exe" (
    set PYEXE="%~dp0python311\python.exe"
    set "PATH=%~dp0python311;%~dp0python311\Scripts;%PATH%"
    echo [+] Using bundled Python 3.11
    goto :checkpip
)

REM ── Try system Python
where python >nul 2>&1
if %ERRORLEVEL%==0 (
    set PYEXE=python
    echo [+] Using system Python
    goto :checkpip
)

REM ── Try py launcher
where py >nul 2>&1
if %ERRORLEVEL%==0 (
    set PYEXE=py -3
    echo [+] Using py launcher
    goto :checkpip
)

echo [!] Python not found. Please install Python 3.9+ from https://www.python.org
echo     and add it to your PATH, then re-run this script.
pause
exit /b 1

:checkpip
echo.
echo [*] Checking dependencies...
%PYEXE% -m pip show flask >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [*] Installing dependencies (first-time setup — may take several minutes)...
    echo     Please wait. Downloading AI models requires internet access.
    echo.
    %PYEXE% -m pip install -r "%~dp0requirements.txt"
    if %ERRORLEVEL% NEQ 0 (
        echo [!] Dependency installation failed. Check your internet connection.
        pause
        exit /b 1
    )
    echo [+] Dependencies installed successfully.
)

echo.
echo [+] Starting VisionMate AI server...
echo.
echo  ┌─────────────────────────────────────────────┐
echo  │   Server:  http://127.0.0.1:5000            │
echo  │   Press Ctrl+C to stop the server           │
echo  └─────────────────────────────────────────────┘
echo.
echo  Opening browser in 3 seconds...
timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:5000"

%PYEXE% "%~dp0app.py"

pause
