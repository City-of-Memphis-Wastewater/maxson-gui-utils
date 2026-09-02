#!/usr/bin/env python3
# src/maxson_gui_utils/blindwindow/blindwindow.py
from __future__ import annotations

import logging
import sys
import pyhabitat

from maxson_gui_utils.textpane import TextPane
from .ansi import strip_ansi
from .registration import (
    register_listener,
    unregister_listener,
    start_ipc_listener,
    stop_ipc_listener,
)
from .streams import GuiStream, TeeStream

logger = logging.getLogger(__name__)


class BlindWindow(TextPane):
    """
    Passive output display window.
    Intercepts sys.stdout/sys.stderr and handles rendering.
    """

    def __init__(
        self,
        master=None,
        autoscroll: bool = True,
        **kwargs,
    ):
        self.autoscroll = autoscroll
        super().__init__(master, **kwargs)

        self._orig_stdout = sys.stdout
        self._orig_stderr = sys.stderr

        # 1. Intercept raw stdout/stderr writes in current process
        self._sys_gui_stream = GuiStream(lambda text: self._safe_append(text, "stdout"))
        sys.stdout = TeeStream(self._orig_stdout, self._sys_gui_stream)
        sys.stderr = TeeStream(self._orig_stderr, self._sys_gui_stream)

        # 2. Register listener for in-process Console() dispatches
        register_listener(self._safe_append)

    def _safe_append(self, text: str, tag: str = "stdout") -> None:
        """Thread-safe append helper for Tkinter mainloop with guaranteed ANSI cleanup."""
        clean_text = strip_ansi(text)
        if not clean_text:
            return
        try:
            self.after_idle(self.append, clean_text, tag)
        except Exception:
            pass

    def destroy(self) -> None:
        """Clean up process I/O streams and unregister dispatch listeners."""
        sys.stdout = self._orig_stdout
        sys.stderr = self._orig_stderr
        unregister_listener(self._safe_append)
        super().destroy()


def start_blindwindow(
    port: int | None = None,
    pipe_name: str | None = None,
) -> None:
    """Launch BlindWindow as a standalone Tkinter app with IPC server attached."""
    if not pyhabitat.tkinter_is_available():
        logger.error("BlindWindow requires Tkinter, not available in this environment.")
        return

    import tkinter as tk

    root = tk.Tk()
    root.title("BlindWindow")

    bw = BlindWindow(root)
    bw.pack(fill="both", expand=True)

    # Attach the external IPC listener using registration module
    start_ipc_listener(
        callback=bw._safe_append,
        port=port,
        pipe_name=pipe_name,
    )

    def _on_close():
        stop_ipc_listener()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        logger.info("BlindWindow closed via KeyboardInterrupt.")


if __name__ == "__main__":
    start_blindwindow()