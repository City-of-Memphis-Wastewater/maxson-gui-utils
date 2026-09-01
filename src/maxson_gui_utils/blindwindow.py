#!/usr/bin/env python3
# src/maxson_gui_utils/blindwindow.py
from __future__ import annotations
import sys
import logging
import pyhabitat
from .textpane import TextPane
from .streams import GuiStream, TeeStream
from .ansi import strip_ansi
from .registration import register_listener, unregister_listener

logger = logging.getLogger(__name__)

class BlindWindow(TextPane):
    """
    Passive output display window.
    Intercepts sys.stdout/sys.stderr and subscribes to registration dispatch events.
    """

    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)

        self._orig_stdout = sys.stdout
        self._orig_stderr = sys.stderr

        # 1. Intercept raw stdout/stderr writes
        self._sys_gui_stream = GuiStream(lambda text: self.append(strip_ansi(text)))
        sys.stdout = TeeStream(self._orig_stdout, self._sys_gui_stream)
        sys.stderr = TeeStream(self._orig_stderr, self._sys_gui_stream)

        # 2. Register listener for Console() dispatch events
        self._listener_cb = lambda text: self.append(strip_ansi(text))
        register_listener(self._listener_cb)

    def destroy(self):
        """Restore process I/O streams and unregister pub/sub on destroy."""
        sys.stdout = self._orig_stdout
        sys.stderr = self._orig_stderr
        unregister_listener(self._listener_cb)
        super().destroy()


def start_blindwindow() -> None:
    """Launch BlindWindow as a standalone Tkinter app."""
    if not pyhabitat.tkinter_is_available():
        logger.error("BlindWindow requires Tkinter, not available in this environment.")
        return

    import tkinter as tk

    root = tk.Tk()
    root.title("BlindWindow")
    bw = BlindWindow(root)
    bw.pack(fill="both", expand=True)
    root.mainloop()

if __name__ == "__main__":
    start_blindwindow()