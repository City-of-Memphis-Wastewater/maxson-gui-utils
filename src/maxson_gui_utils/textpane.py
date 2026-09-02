#!/usr/bin/env python3
# src/maxson_gui_utils/textpane.py

import tkinter as tk
from tkinter import ttk
import pyhabitat

from .tk_utils import set_tk_iconphoto, set_tk_iconbitmap

class TextPane(ttk.Frame):
    """
    Base text display widget with scrollbar and icon initialization.
    Used by REPL, BlindWindow, and custom user GUI components.
    """

    def __init__(self, 
                 master=None, 
                 auto_set_icon: bool = True, 
                 autoscroll: bool = True,
                 **kwargs):
        super().__init__(master, **kwargs)

        self.autoscroll = autoscroll
        
        self.text_widget = tk.Text(
            self,
            wrap="word",
            undo=True,
            height=20,
            width=80,
        )
        self.scrollbar = ttk.Scrollbar(
            self,
            orient="vertical",
            command=self.text_widget.yview,
        )
        self.text_widget.configure(yscrollcommand=self.scrollbar.set)

        self.text_widget.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        if auto_set_icon:
            self._set_icon()

    def _set_icon(self) -> None:
        """Apply icon photo and bitmap to parent top-level window if available."""
        try:
            top_level = self.winfo_toplevel()
            set_tk_iconphoto(root=top_level)
            if pyhabitat.on_windows():
                set_tk_iconbitmap(root=top_level)
        except Exception:
            pass

    def append(self, text: str, tag: str = None) -> None:
        """Append text to the widget."""
        if tag:
            self.text_widget.insert("end", text, tag)
        else:
            self.text_widget.insert("end", text)
        self.text_widget.see("end")

    def clear(self) -> None:
        """Clear all text."""
        self.text_widget.delete("1.0", "end")

    def scroll_to_end(self) -> None:
        """Scroll to the end of the text."""
        self.text_widget.see("end")

