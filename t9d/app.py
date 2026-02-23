"""
numpad_t9.app
=============
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
    Full application.  Instantiate then call :meth:`run`.

    Example::

        from numpad_t9 import NumpadT9, load_config
        app = NumpadT9(load_config())
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
        self.root.title("NumpadT9")

        # ── Overlay ───────────────────────────────────────────────────────────
        self.overlay = OverlayWindow(self.root, config.get("overlay", {}))

        # ── Global keyboard listener ──────────────────────────────────────────
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            suppress=False,
        )

    # ── Key dispatch (listener thread → Tk main thread) ──────────────────────

    def _on_press(self, key: Key | KeyCode) -> None:
        action = self._key_to_action(key)
        if action:
            self.root.after(0, self._handle, action)

    @staticmethod
    def _key_to_action(key: Key | KeyCode) -> str | None:  # noqa: C901
        """Map a pynput key event to a named action string."""
        if key == Key.num_lock:
            return None

        # Numpad keys when Num Lock is OFF (pynput reports these as named keys)
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
            Key.esc:       "cancel",
            Key.enter:     "confirm",
        }
        if key in named:
            return named[key]

        if isinstance(key, KeyCode):
            ch = key.char or ""
            vk = getattr(key, "vk", None)

            if ch in "0123456789":
                return ch
            char_map: dict[str, str] = {
                "*": "backspace",
                "/": "delete_word",
                "+": "next",
                "-": "prev",
                ".": "punct_confirm",
            }
            if ch in char_map:
                return char_map[ch]

            # Windows virtual key codes for numpad (fallback)
            if vk is not None:
                vk_map: dict[int, str] = {
                    96: "0",  97: "1",  98: "2",  99: "3",
                    100: "4", 101: "5", 102: "6", 103: "7",
                    104: "8", 105: "9",
                    106: "backspace",
                    107: "next",
                    109: "prev",
                    110: "punct_confirm",
                    111: "delete_word",
                    13:  "confirm",
                }
                return vk_map.get(vk)

        return None

    # ── Action handler (always runs on Tk main thread) ────────────────────────

    def _handle(self, action: str) -> None:  # noqa: C901
        e = self.engine

        if action in "23456789":
            e.push_digit(action)
            self._refresh()

        elif action == "0":
            if e.has_input:
                self._type(e.confirm() + " ")
            else:
                self._tap(Key.space)
            self.overlay.hide()

        elif action == "1":
            if e.has_input:
                self._type(e.confirm())
                self.overlay.hide()
            punct = self.punct_list[self.punct_index % len(self.punct_list)]
            self.punct_index += 1
            self._type(punct)

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
        """
        Called every 200ms on the Tk main thread.
        Tkinter's mainloop() blocks Python-level signal delivery entirely,
        so Ctrl+C never fires without this periodic re-entry into Python.
        """
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

        # Let Ctrl+C set the stop flag from any thread
        def _sigint_handler(sig, frame):
            self._stop = True

        signal.signal(signal.SIGINT, _sigint_handler)

        self._listener.start()
        self.root.after(200, self._poll_signals)   # kick off the signal poller
        self.root.mainloop()                        # blocks until root.destroy()
        self._listener.stop()
        print("\n[T9] Stopped.")