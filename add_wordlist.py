#!/usr/bin/env python3
"""
add_wordlist.py
===============
Helper utility: import an external word list into the numpad_t9 wordlists
directory, cleaning and deduplicating it in the process.

Can be run directly or after installing the package.

Usage:
    python add_wordlist.py <lang_code> <source_file> [--append]

Examples:
    # Import a German word list → creates wordlists/de.txt
    python add_wordlist.py de /path/to/german_words.txt

    # Append new words to an existing list without overwriting
    python add_wordlist.py en /path/to/extra_english.txt --append
"""

import os
import sys
import argparse
from pathlib import Path

# Resolve wordlists dir: prefer installed package location, fall back to cwd
try:
    import numpad_t9
    _PACKAGE_DIR = Path(numpad_t9.__file__).parent
except ImportError:
    _PACKAGE_DIR = Path(__file__).parent / "numpad_t9"

WORDLIST_DIR = _PACKAGE_DIR / "wordlists"

# Mirror the T9 / diacritic maps from engine.py (kept in sync manually)
T9_MAP = {"2": "abc", "3": "def", "4": "ghi", "5": "jkl",
          "6": "mno", "7": "pqrs", "8": "tuv", "9": "wxyz"}
DIACRITIC_MAP = {
    "å": "2", "ä": "2", "ö": "6",
    "ü": "8", "ß": "7",
    "é": "3", "è": "3", "ê": "3", "ë": "3",
    "à": "2", "â": "2",
    "î": "4", "ï": "4",
    "ô": "6", "œ": "6",
    "ù": "8", "û": "8",
    "ç": "2", "ñ": "6",
    "æ": "2", "ø": "6",
}
VALID_CHARS: set[str] = set()
for _d, _c in T9_MAP.items():
    VALID_CHARS.update(_c)
VALID_CHARS.update(DIACRITIC_MAP.keys())


def is_mappable(word: str) -> bool:
    return all(ch in VALID_CHARS for ch in word.lower())


def load_source(path: Path) -> list[str]:
    words: list[str] = []
    skipped = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            w = line.strip().lower()
            if not w or w.startswith("#"):
                continue
            if is_mappable(w):
                words.append(w)
            else:
                skipped += 1
    if skipped:
        print(f"  Skipped {skipped} word(s) with unmappable characters.")
    return words


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import a plain-text word list into numpad_t9."
    )
    parser.add_argument("lang", help="Language code, e.g. en, sv, de, fr")
    parser.add_argument("source", help="Path to source word list (.txt, one word per line)")
    parser.add_argument(
        "--append", action="store_true",
        help="Append to existing wordlist instead of replacing it.",
    )
    args = parser.parse_args()

    source_path = Path(args.source).resolve()
    if not source_path.exists():
        print(f"ERROR: Source file not found: {source_path}")
        sys.exit(1)

    dest_path = WORDLIST_DIR / f"{args.lang}.txt"
    WORDLIST_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Source : {source_path}")
    new_words = load_source(source_path)
    print(f"Mappable words found: {len(new_words):,}")

    existing: set[str] = set()
    if args.append and dest_path.exists():
        with open(dest_path, "r", encoding="utf-8") as f:
            for line in f:
                w = line.strip().lower()
                if w and not w.startswith("#"):
                    existing.add(w)
        print(f"Existing words in {args.lang}.txt: {len(existing):,}")

    combined = sorted(existing | set(new_words))
    added = len(combined) - len(existing)

    header = (
        f"# {args.lang} word list for Numpad T9\n"
        f"# Imported by add_wordlist.py\n"
        f"# Words: {len(combined):,}\n"
        f"# One word per line. Lines starting with # are ignored.\n\n"
    )

    with open(dest_path, "w", encoding="utf-8") as f:
        f.write(header)
        for word in combined:
            f.write(word + "\n")

    print(f"Written : {dest_path}")
    print(f"Total   : {len(combined):,} words  (+{added} new)")
    print(f"\nAdd '{args.lang}' to the languages list in config.json to activate it.")


if __name__ == "__main__":
    main()