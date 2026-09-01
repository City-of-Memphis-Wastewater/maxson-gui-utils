# src/maxson_gui_utils/blindwindow.py

import sys
import logging
import pyhabitat

from .tk_utils import set_tk_iconphoto, set_tk_iconbitmap

logger = logging.getLogger(__name__)

def start_blindwindow() -> None:
    """Launch BlindWindow as a standalone Tkinter app."""
    if not pyhabitat.tkinter_is_available():
        logger.error("BlindWindow requires Tkinter, not available in this environment.")
        return

    import tkinter as tk
    from .textpane import TextPane
    from .streams import GuiStream, TeeStream
    from .ansi import strip_ansi

    class BlindWindow(TextPane):
        """
        Passive text display that captures stdout/stderr.
        """
        def __init__(self, master=None, **kwargs):
            super().__init__(master, **kwargs)

            self._set_icon()

            # Redirect stdout/stderr
            gui_stream = GuiStream(lambda text: self.append(strip_ansi(text)))
            sys.stdout = TeeStream(sys.stdout, gui_stream)
            sys.stderr = TeeStream(sys.stderr, gui_stream)

        def _set_icon(self):
            top_level = self.winfo_toplevel()
            set_tk_iconphoto(root=top_level)
            if pyhabitat.on_windows():
                set_tk_iconbitmap(root=top_level)

    root = tk.Tk()
    root.title("BlindWindow")
    bw = BlindWindow(root)
    bw.pack(fill="both", expand=True)
    root.mainloop()

if __name__ == "__main__":
    start_blindwindow()
