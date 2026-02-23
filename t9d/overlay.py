"""
numpad_t9.overlay
=================
Frameless floating overlay window (tkinter).
Displays T9 word candidates near the cursor.
"""

from __future__ import annotations

import tkinter as tk


class OverlayWindow:
    """
    A small, always-on-top, frameless window that shows the current T9
    digit sequence and up to ``max_candidates`` word suggestions.
    Repositions itself near the system cursor on every update.
    """

    def __init__(self, root: tk.Tk, overlay_cfg: dict) -> None:
        self.root = root
        self.cfg = overlay_cfg
        self._candidate_labels: list[tk.Label] = []
        self._build()

    # ── Construction ─────────────────────────────────────────────────────────

    def _build(self) -> None:
        self.win = tk.Toplevel(self.root)
        self.win.withdraw()
        self.win.overrideredirect(True)         # no title bar / border
        self.win.attributes("-topmost", True)
        self.win.attributes("-alpha", self.cfg.get("opacity", 0.93))

        self.frame = tk.Frame(self.win, bg="#1a1a2e", padx=14, pady=8)
        self.frame.pack(fill="both", expand=True)

        # Row 1 — digit sequence display
        self.seq_label = tk.Label(
            self.frame,
            text="",
            bg="#1a1a2e",
            fg="#4a9eff",
            font=("Courier New", 10, "bold"),
            anchor="w",
        )
        self.seq_label.pack(fill="x")

        # Row 2+ — candidate words
        self.cand_frame = tk.Frame(self.frame, bg="#1a1a2e")
        self.cand_frame.pack(fill="x", pady=(4, 0))

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _cursor_pos(self) -> tuple[int, int]:
        try:
            return self.root.winfo_pointerx(), self.root.winfo_pointery()
        except Exception:
            return 100, 100

    def _reposition(self) -> None:
        cx, cy = self._cursor_pos()
        ox = self.cfg.get("offset_x", 16)
        oy = self.cfg.get("offset_y", 24)
        self.win.geometry(f"+{cx + ox}+{cy + oy}")

    def _clear_candidates(self) -> None:
        for lbl in self._candidate_labels:
            lbl.destroy()
        self._candidate_labels.clear()

    # ── Public API ────────────────────────────────────────────────────────────

    def update(
        self,
        sequence: list[str],
        candidates: list[str],
        selected_idx: int,
    ) -> None:
        """Refresh content and show the overlay near the cursor."""
        if not sequence:
            self.hide()
            return

        self.seq_label.config(text="  ".join(sequence) + "  ▸")
        self._clear_candidates()

        max_shown = self.cfg.get("max_candidates", 6)
        shown = candidates[:max_shown]

        if not shown:
            lbl = tk.Label(
                self.cand_frame,
                text="   (no match)",
                bg="#1a1a2e",
                fg="#555577",
                font=("Courier New", 11, "italic"),
                anchor="w",
                padx=6,
            )
            lbl.pack(fill="x")
            self._candidate_labels.append(lbl)
        else:
            for i, word in enumerate(shown):
                is_sel = i == selected_idx
                lbl = tk.Label(
                    self.cand_frame,
                    text=f"{'▶ ' if is_sel else '   '}{word}",
                    bg="#e94560" if is_sel else "#1a1a2e",
                    fg="#ffffff" if is_sel else "#a0a0c0",
                    font=("Courier New", 12, "bold" if is_sel else "normal"),
                    anchor="w",
                    padx=6,
                )
                lbl.pack(fill="x", pady=1)
                self._candidate_labels.append(lbl)

        self._reposition()
        self.win.deiconify()
        self.win.lift()

    def hide(self) -> None:
        if self.win:
            self.win.withdraw()

    def show_toast(self, message: str, duration_ms: int = 1600) -> None:
        """Briefly flash a status message (e.g. 'Learned: home')."""
        self._clear_candidates()
        self.seq_label.config(text="")
        lbl = tk.Label(
            self.cand_frame,
            text=f"✓ {message}",
            bg="#1a1a2e",
            fg="#50fa7b",
            font=("Courier New", 11, "bold"),
            anchor="w",
            padx=6,
        )
        lbl.pack(fill="x")
        self._candidate_labels.append(lbl)
        self._reposition()
        self.win.deiconify()
        self.win.lift()
        self.root.after(duration_ms, self.hide)