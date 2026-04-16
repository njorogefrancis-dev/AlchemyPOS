@echo off
REM ============================================================================
REM AlchemyPOS — Windows Build Script
REM Creates EXE and Installer for Windows Distribution
REM ============================================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ╔══════════════════════════════════════════════════════════════════════════╗
echo ║                   AlchemyPOS Windows Build Script                        ║
echo ║               Build EXE and Installer for Distribution                   ║
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
REM Setup Virtual Environment
REM ─────────────────────────────────────────────────────────────────────────
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
) else (
    echo [OK] Virtual environment exists
)
echo.

REM ─────────────────────────────────────────────────────────────────────────
REM Activate Virtual Environment
REM ─────────────────────────────────────────────────────────────────────────
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)
echo [OK] Virtual environment activated
echo.

REM ─────────────────────────────────────────────────────────────────────────
REM Install Dependencies
REM ─────────────────────────────────────────────────────────────────────────
echo [INFO] Installing required packages...
pip install --upgrade pip setuptools wheel >nul 2>&1
pip install pyinstaller reportlab >nul 2>&1

if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
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
if exist "__pycache__" rmdir /s /q __pycache__ >nul 2>&1
echo [OK] Clean complete
echo.

REM ─────────────────────────────────────────────────────────────────────────
REM Build EXE with PyInstaller
REM ─────────────────────────────────────────────────────────────────────────
echo [INFO] Building EXE with PyInstaller...
echo.

pyinstaller ^
    --name "AlchemyPOS" ^
    --onefile ^
    --windowed ^
    --icon=setup_files\icon.ico ^
    --add-data "setup_files;setup_files" ^
    --distpath "dist" ^
    --buildpath "build" ^
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
    echo [INFO] Then run NSIS: "C:\Program Files (x86)\NSIS\makensis.exe" setup_files\installer.nsi
) else (
    echo [INFO] Building installer with NSIS...
    
    REM Check if NSIS is installed
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
        echo [WARN] NSIS not found, skipping installer creation
        echo [INFO] Install NSIS from: https://nsis.sourceforge.io/
        echo [INFO] Then manually run: makensis setup_files\installer.nsi
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
echo [NEXT] Distribution files ready in the 'dist' folder
echo.
pause
