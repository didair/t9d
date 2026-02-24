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
    def __init__(self, config: dict) -> None:
        self.config = config
        self.engine = T9Engine(config)
        self.kb = Controller()
        self.punct_index = 0
        self.punct_list: list[str] = config.get(
            "punctuation",
            [".", ",", "!", "?", "-", "'", '"', "(", ")", ":", ";", "@", "#"],
        )

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("t9d")

        self.overlay = OverlayWindow(self.root, config.get("overlay", {}))

        self._listener = keyboard.Listener(
            on_press=self._on_press,
            suppress=True,
        )

    def _suspend_listener(self):
        try:
            self._listener.stop()
        except Exception:
            pass

    def _resume_listener(self):
        try:
            self._listener = keyboard.Listener(
                on_press=self._on_press,
                suppress=True,
            )
            self._listener.start()
        except Exception:
            pass

    # ── Key dispatch ─────────────────────────────────────────────────────────
    def _on_press(self, key: Key | KeyCode, injected: bool | None = None) -> bool:
        if injected:
            return False

        action = self._key_to_action(key)

        if action:
            print("T9:", key, action)
            self.root.after(0, self._handle, action)
            return True

        # Main Enter confirms only when composing
        if key == Key.enter and self.overlay.is_visible:
            print("T9: Swallow Enter (overlay visible)")
            self.root.after(0, self._handle, "confirm")
            return True

        # Main Backspace cancels composition
        if key == Key.backspace and self.overlay.is_visible:
            print("T9: Cancel composition (main backspace)")
            self.root.after(0, self._handle, "cancel")
            return True  # swallow to avoid deleting wrong char

        print("Regular:", key)
        return False

    @staticmethod
    def _key_to_action(key: Key | KeyCode) -> str | None:
        if key == Key.num_lock:
            return None

        # ── Physical numpad keys (VK codes) ────────────────────────────────
        if isinstance(key, KeyCode):
            vk = getattr(key, "vk", None)

            vk_map = {
                96:  "0",
                97:  "1",
                98:  "2",
                99:  "3",
                100: "4",
                101: "5",
                102: "6",
                103: "7",
                104: "8",
                105: "9",
                106: "backspace",
                107: "next",
                109: "prev",
                110: "punct_confirm",
                111: "delete_word",
                13:  "confirm",
            }

            return vk_map.get(vk)

        if key == Key.esc:
            return "cancel"

        return None

    # ── Action handler ───────────────────────────────────────────────────────

    def _handle(self, action: str) -> None:
        e = self.engine

        if action in "123456789":
            if action == "7":
                if e.has_input:
                    self._type(e.confirm())
                    e.reset()
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
                e.reset()
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
                self._type(e.confirm() + " ")
                e.reset()
                self.overlay.hide()

        elif action == "punct_confirm":
            if e.has_input:
                word = e.current_word
                e.learn_word(word)
                e.confirm()
                e.reset()
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

    # ── Output ───────────────────────────────────────────────────────────────

    def _type(self, text: str) -> None:
        try:
            self._suspend_listener()
            self.kb.type(text)
        finally:
            self._resume_listener()

    def _tap(self, key: Key) -> None:
        try:
            self._suspend_listener()
            self.kb.tap(key)
        finally:
            self._resume_listener()

    def _refresh(self) -> None:
        self.overlay.update(
            self.engine.sequence,
            self.engine.candidates,
            self.engine.candidate_index,
        )

    # ── Run ──────────────────────────────────────────────────────────────────

    def _poll_signals(self) -> None:
        if self._stop:
            self.root.destroy()
            return
        self.root.after(200, self._poll_signals)

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
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