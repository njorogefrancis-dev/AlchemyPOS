# AlchemyPOS Windows Build Instructions

## Prerequisites

### 1. **Python 3.8+**
- Download from: https://www.python.org/downloads/
- **IMPORTANT**: Check "Add Python to PATH" during installation
- Verify: Open Command Prompt and run `python --version`

### 2. **NSIS (Optional - for installer only)**
- Download from: https://nsis.sourceforge.io/Download
- Install to default location: `C:\Program Files (x86)\NSIS\`
- Required only if you want to create the installer `.exe`

### 3. **Icon File (Optional)**
- Place a 256x256 `.ico` file at: `setup_files\icon.ico`
- If not present, PyInstaller will use a default icon

## Quick Start

### Build Everything (EXE + Installer)

1. Open **Command Prompt** (cmd.exe) or **PowerShell**
2. Navigate to the AlchemyPOS folder:
   ```
   cd C:\path\to\AlchemyPOS
   ```
3. Run the build script:
   ```
   build.bat
   ```
4. Wait for completion. Check the `dist\` folder for output files.

### Output Files

- **dist\AlchemyPOS.exe** — Standalone executable
- **dist\AlchemyPOS_Installer.exe** — Windows installer (if NSIS is installed)

## What the Build Script Does

1. ✅ Checks Python installation
2. ✅ Creates a virtual environment
3. ✅ Installs dependencies (PyInstaller, ReportLab)
4. ✅ Cleans previous builds
5. ✅ Builds EXE with PyInstaller
6. ✅ Creates installer with NSIS (if available)

## Troubleshooting

### "Python is not installed or not in PATH"
- Reinstall Python and **check "Add Python to PATH"**
- Restart Command Prompt after installation

### "PyInstaller build failed"
- Run: `pip install --upgrade pyinstaller`
- Make sure the virtual environment activated properly

### "NSIS not found, skipping installer creation"
- Install NSIS: https://nsis.sourceforge.io/Download
- Or run NSIS manually:
  ```
  "C:\Program Files (x86)\NSIS\makensis.exe" setup_files\installer.nsi
  ```

### Executable is too large
- This is normal. PyInstaller bundles Python runtime (~50-80MB)
- To reduce size, use UPX: https://upx.github.io/

## Advanced: Manual Build Steps

If `build.bat` doesn't work, try manual steps:

```batch
REM Create virtual environment
python -m venv venv

REM Activate it
venv\Scripts\activate

REM Install dependencies
pip install pyinstaller reportlab

REM Build EXE
pyinstaller --name AlchemyPOS --onefile --windowed main.py

REM Build installer (if NSIS installed)
"C:\Program Files (x86)\NSIS\makensis.exe" setup_files\installer.nsi
```

## Distribution

Share `dist\AlchemyPOS_Installer.exe` with users:
- Installs to: `C:\Program Files\AlchemyPOS\`
- Creates Start Menu shortcuts
- Can be uninstalled via Control Panel

Users can also use `dist\AlchemyPOS.exe` as a portable executable directly without installation.

## Creating an Icon

1. Create a 256x256 PNG image of your logo
2. Convert to ICO format using an online tool:
   - https://ezgif.com/png-to-ico
   - https://convertio.co/png-ico/
3. Save as `setup_files\icon.ico`
4. Rebuild with `build.bat`

## Notes

- Build script requires Windows Vista or later
- For macOS/Linux equivalent, use `install.sh` and `pyinstaller` directly
- Virtual environment ensures no conflicts with system Python
- Generated EXE is independent and can run on any Windows machine
