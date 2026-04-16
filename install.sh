#!/bin/bash
# AlchemyPOS — Installation Script
# Supports: Kali Linux, Ubuntu, Debian
# Run once: bash install.sh

set -e

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║           AlchemyPOS Installer           ║"
echo "║   Professional POS for Linux             ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── Python 3 ────────────────────────────────────────────────────────────────
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 not found."
    echo "        Install with: sudo apt install python3"
    exit 1
fi
echo "[OK] Python3: $(python3 --version)"

# ── Tkinter ─────────────────────────────────────────────────────────────────
if ! python3 -c "import tkinter" 2>/dev/null; then
    echo "[INFO] Installing python3-tk..."
    sudo apt-get install -y python3-tk
fi
echo "[OK] Tkinter available"

# ── ReportLab (PDF export — optional but recommended) ───────────────────────
if ! python3 -c "import reportlab" 2>/dev/null; then
    echo "[INFO] Installing reportlab (for PDF export)..."
    pip install reportlab --break-system-packages 2>/dev/null \
        || pip install reportlab 2>/dev/null \
        || echo "[WARN] Could not install reportlab — PDF export will be unavailable."
fi
if python3 -c "import reportlab" 2>/dev/null; then
    echo "[OK] ReportLab available (PDF export enabled)"
else
    echo "[WARN] ReportLab not installed — PDF export disabled (CSV/XML still work)"
fi

# ── Launcher permissions ─────────────────────────────────────────────────────
chmod +x run.sh
echo "[OK] run.sh is executable"

# ── Initialise fresh database ────────────────────────────────────────────────
echo "[INFO] Initialising database..."
cd "$(dirname "$0")"
python3 -c "
import sys, os
sys.path.insert(0, '.')
from database.db import init_database
init_database()
print('[OK] Database initialised — alchemypos.db created')
"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║        Installation Complete!            ║"
echo "╠══════════════════════════════════════════╣"
echo "║  Launch:   bash run.sh                   ║"
echo "║            python3 main.py               ║"
echo "║                                          ║"
echo "║  First launch will guide you through     ║"
echo "║  creating your administrator account.    ║"
echo "╚══════════════════════════════════════════╝"
echo ""
