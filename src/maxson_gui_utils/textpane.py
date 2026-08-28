#!/usr/bin/env python3
# src/maxson_gui_utils/textpane.py

import tkinter as tk
from tkinter import ttk

class TextPane(ttk.Frame):
    """
    Base class for text display widgets.
    Shared by REPL and BlindWindow.
    """

    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)

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

    def append(self, text: str, tag: str = None):
        """Append text to the widget."""
        if tag:
            self.text_widget.insert("end", text, tag)
        else:
            self.text_widget.insert("end", text)
        self.text_widget.see("end")

    def clear(self):
        """Clear all text."""
        self.text_widget.delete("1.0", "end")

    def scroll_to_end(self):
        """Scroll to the end of the text."""
        self.text_widget.see("end")


