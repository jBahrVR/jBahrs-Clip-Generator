@echo off
cd /d "%~dp0"
title jBahr's Clip Generator
cls
echo ====================================================
echo   Starting jBahr's Clip Generator...
echo ====================================================

if exist ".venv\Scripts\python.exe" (
    echo [INFO] Launching with Virtual Environment Python...
    ".venv\Scripts\python.exe" app.py
) else (
    echo [INFO] Launching with System Python...
    python app.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ====================================================
    echo   [ERROR] Application exited with code %ERRORLEVEL%
    echo ====================================================
    pause
)
