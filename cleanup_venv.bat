@echo off
timeout /t 2 /nobreak
if exist "venv" (
    echo Removing venv...
    rmdir /s /q venv
    echo Done.
)
