"""
numpad_t9.engine
================
Pure T9 prediction engine — no UI, no keyboard hooks.
Can be imported and used standalone for testing or embedding.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

# ─── T9 character maps ────────────────────────────────────────────────────────

T9_MAP: dict[str, str] = {
    "1": "pqrs",
    "2": "tuv",
    "3": "wxyz",
    "4": "ghi",
    "5": "jkl",
    "6": "mno",
    # 7 = punctuation (no letter group)
    "8": "abc",
    "9": "def",
}

# Diacritic → T9 digit.
# Extend this dict to support additional languages / scripts.
DIACRITIC_MAP: dict[str, str] = {
    # Swedish / Nordic
    "å": "2", "ä": "2", "ö": "6",
    # German
    "ü": "8", "ß": "7",
    # French / Spanish
    "é": "3", "è": "3", "ê": "3", "ë": "3",
    "à": "2", "â": "2",
    "î": "4", "ï": "4",
    "ô": "6", "œ": "6",
    "ù": "8", "û": "8",
    "ç": "2",
    "ñ": "6",
    # Nordic extras
    "æ": "2", "ø": "6",
}


def _build_char_to_digit() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for digit, chars in T9_MAP.items():
        for ch in chars:
            mapping[ch] = digit
    mapping.update(DIACRITIC_MAP)
    return mapping


CHAR_TO_DIGIT: dict[str, str] = _build_char_to_digit()


# ─── Wordlist loader ──────────────────────────────────────────────────────────

def load_wordlist(lang_code: str, wordlist_dir: str) -> list[str]:
    """
    Load ``wordlists/<lang_code>.txt`` and return a list of lowercase words.
    Lines starting with ``#`` are treated as comments and skipped.
    """
    path = Path(wordlist_dir) / f"{lang_code}.txt"
    if not path.exists():
        print(f"[T9] Warning: wordlist not found for '{lang_code}' at {path}")
        return []
    words: list[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            word = line.strip().lower()
            if word and not word.startswith("#"):
                words.append(word)
    print(f"[T9] Loaded {len(words):,} words  [{lang_code}]")
    return words


# ─── Engine ───────────────────────────────────────────────────────────────────

class T9Engine:
    """
    Stateful T9 prediction engine.

    Usage::

        engine = T9Engine(config)
        engine.push_digit("4")
        engine.push_digit("6")
        engine.push_digit("6")
        engine.push_digit("3")
        print(engine.candidates)     # ['home', 'hone', 'gone', ...]
        word = engine.confirm()      # returns 'home', resets sequence
    """

    def __init__(self, config: dict) -> None:
        self.config = config
        self.sequence: list[str] = []
        self.candidates: list[str] = []
        self.candidate_index: int = 0
        self.confirmed_words: list[str] = []

        # digit_string → [word, ...]
        self.lookup: dict[str, list[str]] = {}

        # lang_code → { word: use_count }
        self.user_dicts: dict[str, dict[str, int]] = {}

        self._load_all_wordlists()
        self._load_all_user_dicts()

    # ── Loading ───────────────────────────────────────────────────────────────

    def _load_all_wordlists(self) -> None:
        wordlist_dir = self.config.get("wordlist_dir", "wordlists")
        for lang in self.config.get("languages", ["en"]):
            words = load_wordlist(lang, wordlist_dir)
            self._index_words(words)

    def _load_all_user_dicts(self) -> None:
        user_dict_dir = Path(
            os.path.expanduser(self.config.get("user_dict_dir", "~/.config/numpad_t9"))
        )
        for lang in self.config.get("languages", ["en"]):
            path = user_dict_dir / f"user_{lang}.json"
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        self.user_dicts[lang] = json.load(f)
                    self._index_words(list(self.user_dicts[lang].keys()), prepend=True)
                    print(f"[T9] Loaded {len(self.user_dicts[lang]):,} personal words [{lang}]")
                except Exception as e:
                    print(f"[T9] Warning: could not load {path}: {e}")
                    self.user_dicts[lang] = {}
            else:
                self.user_dicts[lang] = {}

    def _save_user_dict(self, lang: str) -> None:
        user_dict_dir = Path(
            os.path.expanduser(self.config.get("user_dict_dir", "~/.config/numpad_t9"))
        )
        user_dict_dir.mkdir(parents=True, exist_ok=True)
        path = user_dict_dir / f"user_{lang}.json"
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.user_dicts[lang], f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[T9] Could not save user dict ({lang}): {e}")

    # ── Indexing ──────────────────────────────────────────────────────────────

    @staticmethod
    def word_to_digits(word: str) -> str:
        """Convert a word to its T9 digit string. Returns ``""`` if unmappable."""
        result: list[str] = []
        for ch in word.lower():
            digit = CHAR_TO_DIGIT.get(ch)
            if digit is None:
                return ""
            result.append(digit)
        return "".join(result)

    def _index_words(self, words: list[str], prepend: bool = False) -> None:
        for word in words:
            key = self.word_to_digits(word)
            if not key:
                continue
            bucket = self.lookup.setdefault(key, [])
            lower_bucket = [w.lower() for w in bucket]
            if word.lower() in lower_bucket:
                if prepend:
                    idx = lower_bucket.index(word.lower())
                    bucket.insert(0, bucket.pop(idx))
                continue
            if prepend:
                bucket.insert(0, word.lower())
            else:
                bucket.append(word.lower())

    # ── Learning ──────────────────────────────────────────────────────────────

    def learn_word(self, word: str, lang: str | None = None) -> None:
        """Persist a word to the personal dictionary and move it to front of candidates."""
        word = word.strip().lower()
        if not word:
            return
        if lang is None:
            lang = self.config.get("languages", ["en"])[0]
        if lang not in self.user_dicts:
            self.user_dicts[lang] = {}
        self.user_dicts[lang][word] = self.user_dicts[lang].get(word, 0) + 1
        self._save_user_dict(lang)
        self._index_words([word], prepend=True)

    def bump_word(self, word: str) -> None:
        """Increment usage count (called on every normal confirm)."""
        self.learn_word(word)

    def _user_freq(self, word: str) -> int:
        return sum(d.get(word, 0) for d in self.user_dicts.values())

    # ── Sequence management ───────────────────────────────────────────────────

    def push_digit(self, digit: str) -> None:
        """Append a digit and refresh candidates."""
        self.sequence.append(digit)
        self._refresh_candidates()

    def pop_digit(self) -> bool:
        """Remove the last digit. Returns ``True`` if the sequence is still non-empty."""
        if self.sequence:
            self.sequence.pop()
            self._refresh_candidates()
        return bool(self.sequence)

    def reset(self) -> None:
        self.sequence = []
        self.candidates = []
        self.candidate_index = 0

    def _refresh_candidates(self) -> None:
        key = "".join(self.sequence)
        raw = list(self.lookup.get(key, []))
        self.candidates = sorted(raw, key=lambda w: (-self._user_freq(w), w))
        self.candidate_index = 0

    # ── Navigation ────────────────────────────────────────────────────────────

    def cycle_next(self) -> None:
        if self.candidates:
            self.candidate_index = (self.candidate_index + 1) % len(self.candidates)

    def cycle_prev(self) -> None:
        if self.candidates:
            self.candidate_index = (self.candidate_index - 1) % len(self.candidates)

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def current_word(self) -> str:
        if self.candidates:
            return self.candidates[self.candidate_index]
        # Fallback: first letter of each T9 group
        return "".join(T9_MAP.get(d, "?")[0] for d in self.sequence)

    @property
    def has_input(self) -> bool:
        return bool(self.sequence)

    def confirm(self) -> str:
        """Return the selected word, bump its frequency, and reset the sequence."""
        word = self.current_word
        self.bump_word(word)
        self.confirmed_words.append(word)
        self.reset()
        return word