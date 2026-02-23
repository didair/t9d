# t9d

System-wide T9 predictive text input via the numpad — multi-language, with a
floating word-candidate overlay and a personal learning dictionary.

---

## Installation

```bash
git clone https://github.com/didair/t9d.git
cd t9d

# One-command setup — creates a venv and installs everything (≈ npm install)
python setup_venv.py

# With dev tools (pytest, ruff, mypy)
python setup_venv.py --dev

# Start fresh
python setup_venv.py --reset
```

The script handles everything: creates `.venv/`, upgrades pip inside it, and
installs the package in editable mode so your local edits take effect
immediately — no reinstall needed.

> **Why a venv?** Modern Linux distros (Debian, Ubuntu, Arch) protect the
> system Python from `pip install`. A virtual environment is the standard
> fix — identical to how `node_modules/` keeps npm packages local to a project.

### Manual setup (if you prefer)

```bash
python3 -m venv .venv

# Linux / macOS
source .venv/bin/activate
pip install -e .

# Windows
.venv\Scripts\activate
pip install -e .
```

After activating the venv, the `t9d` command is available

---

## Running

```bash
t9d                          # start with config.json defaults
t9d --lang en,sv             # override languages on the fly
t9d --config /my/config.json # use a custom config file
t9d --list-langs             # show available wordlists and exit
```

---

## Project Structure

```
t9d/
│
├── pyproject.toml          ← package manifest (≈ package.json)
│
├── t9d/              ← installable Python package
│   ├── __init__.py         ← public API
│   ├── cli.py              ← entry point (t9d command)
│   ├── app.py              ← keyboard listener + event handling
│   ├── engine.py           ← pure T9 logic (no UI)
│   ├── overlay.py          ← floating tkinter overlay
│   ├── config.py           ← config loader
│   ├── config.json         ← default configuration
│   └── wordlists/
│       ├── en.txt          ← English
│       └── sv.txt          ← Swedish
│
├── tests/
│   └── test_engine.py      ← pytest unit tests
│
└── add_wordlist.py         ← helper: import external word lists
```

### npm ↔ pip equivalents

| npm / Node               | pip / Python                          |
|--------------------------|---------------------------------------|
| `package.json`           | `pyproject.toml`                      |
| `npm install`            | `python setup_venv.py`                |
| `npm install --save-dev` | `python setup_venv.py --dev`          |
| `node_modules/`          | `.venv/`                              |
| `npm run <script>`       | registered console script             |
| `npx`                    | `pipx run t9d`                        |
| `rm -rf node_modules`    | `python setup_venv.py --reset`        |

---

## Controls

| Key       | Action                                          |
|-----------|-------------------------------------------------|
| `2` – `9` | Append T9 digit to current sequence             |
| `0`       | Confirm current word + type a space             |
| `1`       | Cycle punctuation  `. , ! ? - ' " ( )`          |
| `*`       | Delete last digit                               |
| `/`       | Delete last confirmed word                      |
| `+`       | Next word candidate                             |
| `-`       | Previous word candidate                         |
| `Enter`   | Confirm selected candidate                      |
| `.`       | Confirm + **save to personal dictionary**       |
| `Esc`     | Cancel current sequence                         |

---

## Language Configuration

Edit `t9d/config.json` (or supply your own via `--config`):

```json
{ "languages": ["en"] }          // English only
{ "languages": ["sv"] }          // Swedish only
{ "languages": ["en", "sv"] }    // Merged — both active at once
```

---

## Adding a New Language

1. Create `t9d/wordlists/xx.txt` — one word per line, `#` for comments.
2. Or use the import helper:

```bash
python add_wordlist.py de /path/to/german_words.txt
```

3. Add `"xx"` to `languages` in `config.json` and restart.

### Diacritic support

Characters with diacritics are mapped to T9 digits via `DIACRITIC_MAP` in
`t9d/engine.py`:

| Characters              | T9 key | Languages              |
|------------------------|--------|------------------------|
| å, ä, à, â, æ, ç       | 2      | Swedish, French        |
| é, è, ê, ë             | 3      | French, Spanish        |
| î, ï                   | 4      | French                 |
| ö, ô, œ, ø, ñ          | 6      | Swedish, French, Spanish |
| ü, ù, û                | 8      | German, French         |
| ß                      | 7      | German                 |

To add more, edit `DIACRITIC_MAP` in `engine.py`:

```python
DIACRITIC_MAP: dict[str, str] = {
    "ő": "6",   # Hungarian
    ...
}
```

---

## Development

```bash
# Install with dev tools
python setup_venv.py --dev
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Run tests
pytest

# Run tests with coverage
pytest --cov=t9d

# Lint + format check
ruff check .
ruff format --check .

# Type check
mypy t9d/
```

---

## Personal Dictionary

Words confirmed with `Numpad .` are saved per-language:

```
~/.config/t9d/
├── user_en.json
├── user_sv.json
└── user_xx.json
```

Configure the path via `user_dict_dir` in `config.json`.

---

## config.json Reference

```jsonc
{
  "languages": ["en"],              // active wordlists
  "wordlist_dir": "wordlists",      // relative to config file
  "user_dict_dir": "~/.config/t9d",

  "overlay": {
    "max_candidates": 6,
    "offset_x": 16,
    "offset_y": 24,
    "opacity": 0.93
  },

  "punctuation": [".", ",", "!", "?", "-", "'", "\"", "(", ")", ":", ";"]
}
```

---

## Platform Notes

### Windows
Works out of the box.

### macOS
Grant **Accessibility** permissions to your terminal:
System Preferences → Privacy & Security → Accessibility → add your terminal app.

### Linux
```bash
# Option A: run with sudo
sudo t9d

# Option B: add to input group (persistent, no sudo needed after)
sudo usermod -aG input $USER
# log out and back in
t9d
```

If `tkinter` is missing: `sudo apt install python3-tk`

---

## Run on Startup

### Windows
Shortcut to `pythonw -m t9d` in `shell:startup`.

### macOS — launchd
```xml
<!-- ~/Library/LaunchAgents/com.user.t9d.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key>        <string>com.user.t9d</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/local/bin/t9d</string>
  </array>
  <key>RunAtLoad</key>    <true/>
</dict></plist>
```
```bash
launchctl load ~/Library/LaunchAgents/com.user.t9d.plist
```

### Linux — systemd
```ini
# ~/.config/systemd/user/t9d.service
[Unit]
Description=Numpad T9 Translator
[Service]
ExecStart=/usr/local/bin/t9d
Restart=on-failure
[Install]
WantedBy=default.target
```
```bash
systemctl --user enable --now numpad_t9
```