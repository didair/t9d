"""
t9d.app
=======
Main application class: wires together the keyboard listener,
T9 engine, and overlay window.
"""

from __future__ import annotations

import tkinter as tk

try:
    from pynput import keyboard
    from pynput.keyboard import Key, KeyCode, Controller
except ImportError as exc:
    raise ImportError(
        "pynput is required.\n"
        "Install it with:  pip install pynput\n"
        "Or, from the repo:  pip install -e ."
    ) from exc

from .engine import T9Engine
from .overlay import OverlayWindow


class T9App:
    """
    Full application. Instantiate then call :meth:`run`.

    Example::

        from t9d import T9App, load_config
        app = T9App(load_config())
        app.run()
    """

    def __init__(self, config: dict) -> None:
        self.config = config
        self.engine = T9Engine(config)
        self.kb = Controller()
        self.punct_index = 0
        self.punct_list: list[str] = config.get(
            "punctuation",
            [".", ",", "!", "?", "-", "'", '"', "(", ")", ":", ";", "@", "#"],
        )

        # ── Tkinter root (hidden — used only for after() scheduling) ──────────
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("t9d")

        # ── Overlay ───────────────────────────────────────────────────────────
        self.overlay = OverlayWindow(self.root, config.get("overlay", {}))

        # ── Injected-key guard ────────────────────────────────────────────────
        # When we re-inject non-numpad keys (so regular typing still works),
        # the suppress=True listener would catch them again → infinite loop.
        # We break the loop by tagging injected keys in this set and skipping
        # them when we see them come back through the listener.
        self._injecting: set[int] = set()

        # ── Global keyboard listener ──────────────────────────────────────────
        # suppress=True intercepts every key before it reaches other apps.
        # Numpad keys are consumed silently (handled by T9).
        # All other keys are re-injected via self.kb so they pass through
        # normally — the _injecting guard prevents the re-injection loop.
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
            suppress=True,
        )

    # ── Key dispatch (listener thread → Tk main thread) ──────────────────────

    def _on_press(self, key: Key | KeyCode) -> None:
        # If this is a key we injected ourselves, let it pass — don't re-handle.
        key_id = id(key)
        if key_id in self._injecting:
            self._injecting.discard(key_id)
            return

        action = self._key_to_action(key)
        if action:
            # Numpad key — handle via T9, suppress the raw character.
            self.root.after(0, self._handle, action)
        else:
            # Non-numpad key — re-inject so it reaches the active window.
            try:
                self._injecting.add(id(key))
                self.kb.press(key)
            except Exception:
                self._injecting.discard(id(key))

    def _on_release(self, key: Key | KeyCode) -> None:
        key_id = id(key)
        if key_id in self._injecting:
            self._injecting.discard(key_id)
            return
        if not self._key_to_action(key):
            try:
                self._injecting.add(id(key))
                self.kb.release(key)
            except Exception:
                self._injecting.discard(id(key))

    @staticmethod
    def _key_to_action(key: Key | KeyCode) -> str | None:  # noqa: C901
        """
        Map a pynput key event to a named action string.
        Only matches physical numpad keys (Num Lock ON = VK codes 96-111).
        Regular keyboard keys are never matched and pass through untouched.
        """
        if key == Key.num_lock:
            return None

        # ── Windows / Num Lock ON: VK codes 96-111 are numpad-exclusive ───────
        if isinstance(key, KeyCode):
            vk = getattr(key, "vk", None)
            if vk is not None:
                vk_map: dict[int, str] = {
                    96:  "0",   # KP 0 → space / confirm
                    97:  "1",   # KP 1 → PQRS
                    98:  "2",   # KP 2 → TUV
                    99:  "3",   # KP 3 → WXYZ
                    100: "4",   # KP 4 → GHI
                    101: "5",   # KP 5 → JKL
                    102: "6",   # KP 6 → MNO
                    103: "7",   # KP 7 → punctuation
                    104: "8",   # KP 8 → ABC
                    105: "9",   # KP 9 → DEF
                    106: "backspace",      # KP *
                    107: "next",           # KP +
                    109: "prev",           # KP -
                    110: "punct_confirm",  # KP .
                    111: "delete_word",    # KP /
                    13:  "confirm",        # KP Enter
                }
                return vk_map.get(vk)
            return None

        # ── Num Lock OFF: named navigation keys (fallback) ────────────────────
        named: dict[Key, str] = {
            Key.insert:    "0",
            Key.end:       "1",
            Key.down:      "2",
            Key.page_down: "3",
            Key.left:      "4",
            Key.right:     "6",
            Key.home:      "7",
            Key.up:        "8",
            Key.page_up:   "9",
            Key.delete:    "punct_confirm",
        }
        if key in named:
            return named[key]

        if key == Key.esc:
            return "cancel"
        if key == Key.enter:
            return "confirm"

        return None

    # ── Action handler (always runs on Tk main thread) ────────────────────────

    def _handle(self, action: str) -> None:  # noqa: C901
        e = self.engine

        if action in "123456789":
            # Key 7 is punctuation-only (no letter group)
            if action == "7":
                if e.has_input:
                    self._type(e.confirm())
                    self.overlay.hide()
                punct = self.punct_list[self.punct_index % len(self.punct_list)]
                self.punct_index += 1
                self._type(punct)
            else:
                e.push_digit(action)
                self._refresh()

        elif action == "0":
            if e.has_input:
                self._type(e.confirm() + " ")
            else:
                self._tap(Key.space)
            self.overlay.hide()

        elif action == "next":
            if e.has_input:
                e.cycle_next()
                self._refresh()

        elif action == "prev":
            if e.has_input:
                e.cycle_prev()
                self._refresh()

        elif action == "confirm":
            if e.has_input:
                self._type(e.confirm())
                self.overlay.hide()

        elif action == "punct_confirm":
            if e.has_input:
                word = e.current_word
                e.learn_word(word)
                e.confirm()
                self._type(word)
                self.overlay.show_toast(f"Learned: {word}")
            else:
                self._type(".")

        elif action == "backspace":
            if e.has_input:
                e.pop_digit()
                if e.has_input:
                    self._refresh()
                else:
                    self.overlay.hide()
            else:
                self._tap(Key.backspace)

        elif action == "delete_word":
            if e.confirmed_words:
                last = e.confirmed_words.pop()
                for _ in range(len(last) + 1):
                    self._tap(Key.backspace)
            elif not e.has_input:
                self._tap(Key.backspace)

        elif action == "cancel":
            e.reset()
            self.overlay.hide()

    # ── Typing helpers ────────────────────────────────────────────────────────

    def _type(self, text: str) -> None:
        try:
            self.kb.type(text)
        except Exception as ex:
            print(f"[T9] Type error: {ex}")

    def _tap(self, key: Key) -> None:
        try:
            self.kb.tap(key)
        except Exception as ex:
            print(f"[T9] Tap error: {ex}")

    def _refresh(self) -> None:
        self.overlay.update(
            self.engine.sequence,
            self.engine.candidates,
            self.engine.candidate_index,
        )

    # ── Run ───────────────────────────────────────────────────────────────────

    def _poll_signals(self) -> None:
        if self._stop:
            self.root.destroy()
            return
        self.root.after(200, self._poll_signals)

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        """Start the keyboard listener and enter the Tk event loop."""
        import signal

        self._stop = False

        def _sigint_handler(sig, frame):
            self._stop = True

        signal.signal(signal.SIGINT, _sigint_handler)

        self._listener.start()
        self.root.after(200, self._poll_signals)
        self.root.mainloop()
        self._listener.stop()
        print("\n[T9] Stopped.")