# src/maxson_gui_utils/repl.py

import code
import tkinter as tk
from tkinter import ttk
from .textpane import TextPane

class ReplPane(TextPane):
    """
    Tkinter-based REPL widget.
    Can be used interactively (input enabled) or as BlindWindow (input disabled).
    """

    def __init__(self, master=None, input_enabled=True, locals=None, **kwargs):
        super().__init__(master, **kwargs)
        self.input_enabled = input_enabled
        self.locals = locals or {}
        self.console = code.InteractiveConsole(self.locals)

        if self.input_enabled:
             self.text_widget.bind("<Return>", self._on_enter)

    def _on_enter(self, event):
        line = self.text_widget.get("insert linestart", "insert lineend")
        self.append("\n") # move cursor
        self._evaluate(line.strip())
        return "break"

    def _evaluate(self, line: str):
        if not line:
            return
        if line in self.locals and callable(self.locals[line]):
            # allow "quit" instead of "quit()"
            self.locals[line]()
            return
        more = self.console.push(line)
        if more:
            self.append("... ")
        else:
            self.append("\n")

    def append(self, text: str, tag: str = None):
        super().append(text, tag)
