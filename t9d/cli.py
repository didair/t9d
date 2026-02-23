"""
numpad_t9.cli
=============
Command-line entry point.
Registered as the ``t9d`` console script in pyproject.toml.

Usage:
    t9d                        # use config.json in cwd or package default
    t9d --config /my/path.json # explicit config file
    t9d --lang en,sv           # override languages on the fly
    t9d --list-langs           # show available wordlists and exit
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _list_languages(wordlist_dir: str) -> None:
    wdir = Path(wordlist_dir)
    if not wdir.exists():
        print(f"Wordlist directory not found: {wdir}")
        return
    files = sorted(wdir.glob("*.txt"))
    if not files:
        print(f"No wordlists found in {wdir}")
        return
    print(f"Available languages in {wdir}:\n")
    for f in files:
        lines = sum(
            1 for ln in f.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#")
        )
        print(f"  {f.stem:<10}  {lines:>6,} words   ({f.name})")
    print()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="t9d",
        description="System-wide T9 predictive input via the numpad.",
    )
    parser.add_argument(
        "--config", "-c",
        metavar="PATH",
        help="Path to a custom config.json (overrides default resolution order).",
    )
    parser.add_argument(
        "--lang", "-l",
        metavar="CODES",
        help="Comma-separated language codes to activate, e.g. en,sv  (overrides config).",
    )
    parser.add_argument(
        "--list-langs",
        action="store_true",
        help="List available wordlists and exit.",
    )
    args = parser.parse_args(argv)

    # Import here so the CLI is importable even if pynput isn't installed yet
    # (lets `--list-langs` work without a full dep install).
    from .config import load_config

    config = load_config(args.config)

    if args.list_langs:
        _list_languages(config["wordlist_dir"])
        sys.exit(0)

    if args.lang:
        config["languages"] = [c.strip() for c in args.lang.split(",") if c.strip()]

    # Print startup banner
    langs = ", ".join(config.get("languages", ["en"]))
    print("=" * 54)
    print("  Numpad T9 Translator — active")
    print("=" * 54)
    print(f"  Languages : {langs}")
    print(f"  Dict dir  : {config.get('user_dict_dir')}")
    print("-" * 54)
    print("  2-9 : T9 input        0   : space / confirm")
    print("  1   : punctuation     *   : backspace digit")
    print("  /   : delete word     +   : next candidate")
    print("  -   : prev candidate  Ent : confirm word")
    print("  .   : confirm+learn   Esc : cancel")
    print("=" * 54)
    print("  Press Ctrl+C to quit\n")

    from .app import T9App
    app = T9App(config)
    app.run()


if __name__ == "__main__":
    main()