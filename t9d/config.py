"""
numpad_t9.config
================
Loads and validates config.json.
Falls back to sane defaults if the file is missing or partially specified.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

# The package ships a default config.json alongside this file.
_PACKAGE_DIR = Path(__file__).parent
_DEFAULT_CONFIG_PATH = _PACKAGE_DIR / "config.json"

# Users can also place a config.json next to their working directory or set
# an environment variable to point to a custom one.
_ENV_CONFIG = os.environ.get("NUMPAD_T9_CONFIG")


DEFAULTS: dict = {
    "languages": ["en"],
    "wordlist_dir": str(_PACKAGE_DIR / "wordlists"),
    "user_dict_dir": "~/.config/numpad_t9",
    "overlay": {
        "max_candidates": 6,
        "offset_x": 16,
        "offset_y": 24,
        "opacity": 0.93,
    },
    "punctuation": [".", ",", "!", "?", "-", "'", '"', "(", ")", ":", ";", "@", "#"],
}


def load_config(path: str | Path | None = None) -> dict:
    """
    Load configuration from a JSON file and merge with defaults.

    Resolution order (first found wins):
        1. Explicit ``path`` argument
        2. ``NUMPAD_T9_CONFIG`` environment variable
        3. ``config.json`` in the current working directory
        4. Packaged default ``numpad_t9/config.json``

    Returns a fully-populated config dict.
    """
    import copy
    cfg = copy.deepcopy(DEFAULTS)

    candidates: list[Path] = []
    if path:
        candidates.append(Path(path))
    if _ENV_CONFIG:
        candidates.append(Path(_ENV_CONFIG))
    candidates.append(Path.cwd() / "config.json")
    candidates.append(_DEFAULT_CONFIG_PATH)

    for candidate in candidates:
        if candidate.exists():
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    user = json.load(f)
                # Strip comment keys (keys starting with _)
                user = {k: v for k, v in user.items() if not k.startswith("_")}
                # Deep-merge overlay sub-dict
                if "overlay" in user:
                    cfg["overlay"].update(user.pop("overlay"))
                cfg.update(user)
                # Resolve wordlist_dir relative to the config file's location
                if not Path(cfg["wordlist_dir"]).is_absolute():
                    cfg["wordlist_dir"] = str(candidate.parent / cfg["wordlist_dir"])
            except Exception as e:
                print(f"[T9] Warning: could not parse {candidate}: {e}")
            break   # stop at first found

    return cfg