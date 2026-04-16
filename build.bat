@echo off
REM ============================================================================
REM AlchemyPOS — Windows Build Script
REM Creates EXE and Installer for Windows Distribution
REM ============================================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

if /I "%~1"=="clean" (
    echo [INFO] Cleaning generated artifacts...
    if exist "build" rmdir /s /q build >nul 2>&1
    if exist "dist" rmdir /s /q dist >nul 2>&1
    if exist "venv" rmdir /s /q venv >nul 2>&1
    for /d /r . %%d in (__pycache__) do if exist "%%d" rmdir /s /q "%%d" >nul 2>&1
    del /s /q *.pyc >nul 2>&1
    echo [OK] Clean complete
    exit /b 0
)

echo.
echo ╔══════════════════════════════════════════════════════════════════════════╗
echo ║                   AlchemyPOS Windows Build Script                        ║
echo ║               Build EXE and Installer for Windows Distribution           ║
echo ╚══════════════════════════════════════════════════════════════════════════╝
echo.

REM ─────────────────────────────────────────────────────────────────────────
REM Check Python Installation
REM ─────────────────────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo.
    echo Download from: https://www.python.org/downloads/
    echo NOTE: You MUST check "Add Python to PATH" during installation!
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo [OK] %PYTHON_VERSION%
echo.

REM ─────────────────────────────────────────────────────────────────────────
REM Install Build Dependencies
REM ─────────────────────────────────────────────────────────────────────────
echo [INFO] Installing build dependencies...
python -m pip install --upgrade pip
python -m pip install pyinstaller reportlab

if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    echo [INFO] Try: python -m pip install pyinstaller reportlab
    pause
    exit /b 1
)
echo [OK] Dependencies installed
echo.

REM ─────────────────────────────────────────────────────────────────────────
REM Clean Previous Builds
REM ─────────────────────────────────────────────────────────────────────────
echo [INFO] Cleaning previous builds...
if exist "build" rmdir /s /q build >nul 2>&1
if exist "dist" rmdir /s /q dist >nul 2>&1
if exist "venv" rmdir /s /q venv >nul 2>&1
for /d /r . %%d in (__pycache__) do if exist "%%d" rmdir /s /q "%%d" >nul 2>&1
del /s /q *.pyc >nul 2>&1
echo [OK] Clean complete
echo.

REM ─────────────────────────────────────────────────────────────────────────
REM Build EXE with PyInstaller
REM ─────────────────────────────────────────────────────────────────────────
echo [INFO] Building EXE with PyInstaller...
echo.

set "SETUP_DIR=%cd%\setup_files"
set "ICON_ARG="
if exist "%SETUP_DIR%\icon.ico" (
    set "ICON_ARG=--icon=%SETUP_DIR%\icon.ico"
) else (
    echo [WARN] Icon file not found, building without custom icon.
)

python -m PyInstaller ^
    --name "AlchemyPOS" ^
    --onefile ^
    --windowed ^
    %ICON_ARG% ^
    --add-data "%SETUP_DIR%;setup_files" ^
    --distpath "dist" ^
    --workpath "build" ^
    --specpath "build" ^
    main.py

if errorlevel 1 (
    echo [ERROR] PyInstaller build failed
    pause
    exit /b 1
)
echo [OK] EXE created: dist\AlchemyPOS.exe
echo.

REM ─────────────────────────────────────────────────────────────────────────
REM Create Installer (NSIS)
REM ─────────────────────────────────────────────────────────────────────────
if not exist "setup_files\installer.nsi" (
    echo [WARN] NSIS installer script not found at setup_files\installer.nsi
    echo [INFO] To create an installer, install NSIS from: https://nsis.sourceforge.io/
) else (
    echo [INFO] Building installer with NSIS...
    
    if exist "C:\Program Files (x86)\NSIS\makensis.exe" (
        "C:\Program Files (x86)\NSIS\makensis.exe" setup_files\installer.nsi
        if errorlevel 1 (
            echo [ERROR] NSIS build failed
            pause
            exit /b 1
        )
        echo [OK] Installer created
    ) else if exist "C:\Program Files\NSIS\makensis.exe" (
        "C:\Program Files\NSIS\makensis.exe" setup_files\installer.nsi
        if errorlevel 1 (
            echo [ERROR] NSIS build failed
            pause
            exit /b 1
        )
        echo [OK] Installer created
    ) else (
        echo [WARN] NSIS not found at standard locations
        echo [INFO] Install NSIS from: https://nsis.sourceforge.io/
    )
)
echo.

REM ─────────────────────────────────────────────────────────────────────────
REM Build Summary
REM ─────────────────────────────────────────────────────────────────────────
echo ╔══════════════════════════════════════════════════════════════════════════╗
echo ║                        BUILD COMPLETE                                    ║
echo ╚══════════════════════════════════════════════════════════════════════════╝
echo.
echo [OUTPUT] Executable: dist\AlchemyPOS.exe
if exist "dist\AlchemyPOS_Installer.exe" (
    echo [OUTPUT] Installer: dist\AlchemyPOS_Installer.exe
)
echo.
echo [READY] To run: dist\AlchemyPOS.exe
echo [HINT] Use: build.bat clean  (to remove generated build artifacts)
echo.
pause
