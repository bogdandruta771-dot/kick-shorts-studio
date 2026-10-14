@echo off
setlocal enabledelayedexpansion
title Kick Casino Shorts Studio Launcher

echo ============================================================
echo   🎰 Kick Casino Stream-to-Shorts Automation Studio
echo ============================================================
echo.

cd /d "%~dp0"

:: 1. Verify Python availability
where python >nul 2>&1
if %errorlevel% neq 0 (
    where py >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Python is not installed or not in PATH!
        echo Please install Python 3.10+ and re-run.
        pause
        exit /b 1
    ) else (
        set "PYTHON_EXE=py"
    )
) else (
    set "PYTHON_EXE=python"
)

:: 2. Prepend local bin directory for FFmpeg
set "PATH=%~dp0bin;%PATH%"

:: 3. Run bootstrap environment & dependency verification
echo [STEP 1/2] Verifying environment & dependencies...
%PYTHON_EXE% install_dependencies.py
if %errorlevel% neq 0 (
    echo [WARNING] Dependency verification returned warnings. Attempting to start...
)

:: 4. Launch Studio Web App
echo.
echo [STEP 2/2] Launching Kick Shorts Studio UI at http://127.0.0.1:7860...
echo (Press Ctrl+C in this terminal window to stop the server)
echo.

%PYTHON_EXE% app.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Application exited unexpectedly with code %errorlevel%.
    pause
)
