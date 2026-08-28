# src/maxson_gui_utils/blindwindow.py

import sys
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

        # Redirect stdout/stderr
        gui_stream = GuiStream(lambda text: self.append(strip_ansi(text)))
        sys.stdout = TeeStream(sys.stdout, gui_stream)
        sys.stderr = TeeStream(sys.stderr, gui_stream)

def start_blindwindow() -> None:
    """Launch BlindWindow as a standalone Tkinter app."""
    root = tk.Tk()
    root.title("BlindWindow")
    bw = BlindWindow(root)
    bw.pack(fill="both", expand=True)
    root.mainloop()

if __name__ == "__main__":
    start_blindwindow()
