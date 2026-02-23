#!/usr/bin/env python3
"""
setup_venv.py
=============
Creates a virtual environment and installs t9d into it.
Works on Windows, macOS, and Linux — no admin rights needed.

Usage:
    python3 setup_venv.py           # install normally
    python3 setup_venv.py --dev     # also install dev tools (pytest, ruff, mypy)
    python3 setup_venv.py --reset   # delete venv and reinstall from scratch
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

VENV_DIR = Path(__file__).parent / ".venv"
IS_WINDOWS = sys.platform == "win32"
VENV_BIN = VENV_DIR / ("Scripts" if IS_WINDOWS else "bin")


def venv_python() -> Path:
    """Return the Python executable inside the venv, trying common names."""
    for name in ("python", "python3", "python.exe"):
        p = VENV_BIN / name
        if p.exists():
            return p
    # Fallback — let the OS resolve it (will likely fail with a clear message)
    return VENV_BIN / "python"


def venv_pip() -> Path:
    for name in ("pip", "pip3", "pip.exe"):
        p = VENV_BIN / name
        if p.exists():
            return p
    return VENV_BIN / "pip"


def run(cmd: list, **kwargs):
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        sys.exit(result.returncode)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev",   action="store_true", help="Install dev dependencies too")
    parser.add_argument("--reset", action="store_true", help="Delete and recreate the venv")
    args = parser.parse_args()

    # ── Reset: forcibly remove the venv directory ─────────────────────────────
    if args.reset:
        if VENV_DIR.exists():
            print(f"Removing existing venv at {VENV_DIR} ...")
            shutil.rmtree(VENV_DIR, ignore_errors=True)
            if VENV_DIR.exists():
                # shutil failed (e.g. permission issue) — try os.system as fallback
                os.system(f"rm -rf '{VENV_DIR}'")
        else:
            print("No existing venv found, creating fresh one.")

    # ── Create venv ───────────────────────────────────────────────────────────
    if not VENV_DIR.exists():
        print(f"\nCreating virtual environment at {VENV_DIR} ...")
        result = subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)])
        if result.returncode != 0:
            print()
            print("ERROR: Failed to create a virtual environment.")
            print("On Debian/Ubuntu, the venv module is a separate package.")
            print("Fix it with:")
            print()
            print("  sudo apt install python3-venv python3-pip")
            print()
            sys.exit(1)
    else:
        print(f"\nVirtual environment already exists at {VENV_DIR}")

    # ── Bootstrap pip if it is missing from the venv ─────────────────────────
    if not venv_pip().exists():
        print("\nPip not found in venv — bootstrapping with ensurepip ...")
        result = subprocess.run([str(venv_python()), "-m", "ensurepip", "--upgrade"])
        if result.returncode != 0:
            print()
            print("ERROR: ensurepip failed.")
            print("Fix it with:")
            print()
            print("  sudo apt install python3-pip")
            print("  python3 setup_venv.py --reset")
            print()
            sys.exit(1)

    # ── Upgrade pip inside the venv ───────────────────────────────────────────
    print("\nUpgrading pip ...")
    run([str(venv_python()), "-m", "pip", "install", "--upgrade", "pip", "-q"])

    # ── Install the package ───────────────────────────────────────────────────
    extras = "[dev]" if args.dev else ""
    print(f"\nInstalling t9d{extras} ...")
    run([str(venv_pip()), "install", "-e", f".{extras}"])

    # ── Done — print activation instructions ─────────────────────────────────
    if IS_WINDOWS:
        activate_cmd = ".venv\\Scripts\\activate"
    elif os.environ.get("SHELL", "").endswith("fish"):
        activate_cmd = "source .venv/bin/activate.fish"
    else:
        activate_cmd = "source .venv/bin/activate"

    t9d_cmd = str(VENV_BIN / ("t9d.exe" if IS_WINDOWS else "t9d"))

    print()
    print("=" * 54)
    print("  Installation complete!")
    print("=" * 54)
    print()
    print("  Option A — activate the venv, then use the command:")
    print(f"    {activate_cmd}")
    print(f"    t9d")
    print()
    print("  Option B — run directly without activating:")
    print(f"    {t9d_cmd}")
    print()
    if args.dev:
        pytest_cmd = str(VENV_BIN / ("pytest.exe" if IS_WINDOWS else "pytest"))
        print("  Run tests:")
        print(f"    {pytest_cmd}")
        print()
    print("=" * 54)


if __name__ == "__main__":
    main()