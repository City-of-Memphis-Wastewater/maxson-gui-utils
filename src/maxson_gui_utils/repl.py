# src/maxson_gui_utils/repl.py
from __future__ import annotations
import code
import tkinter as tk
from tkinter import ttk
from .textpane import TextPane

class ReplPaneDefunct(TextPane):
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


# ---

#!/usr/bin/env python3
# src/maxson_gui_utils/repl.py

from __future__ import annotations

import code
import sys
from typing import Any, Dict, Optional

from .streams import GuiStream, TeeStream
from .textpane import TextPane


class ReplPane(TextPane):
    """
    Tkinter-based interactive REPL widget.
    Extends TextPane to evaluate Python commands via code.InteractiveConsole.
    """

    def __init__(
        self,
        master: Any = None,
        input_enabled: bool = True,
        locals: Optional[Dict[str, Any]] = None,
        banner: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, **kwargs)
        self.input_enabled = input_enabled
        self.locals = locals if locals is not None else {}
        self.console = code.InteractiveConsole(self.locals)

        self._prompt = ">>> "
        self._more_prompt = "... "

        if banner:
            self.append(f"{banner}\n", tag="stdout")
        
        if self.input_enabled:
            self.append(self._prompt, tag="stdout")
            self.text_widget.bind("<Return>", self._on_enter)

    def _on_enter(self, event: Any) -> str:
        # Extract the line currently under the cursor
        line_text = self.text_widget.get("insert linestart", "insert lineend")

        # Strip off leading prompt prefixes if present
        if line_text.startswith(self._prompt):
            line_text = line_text[len(self._prompt) :]
        elif line_text.startswith(self._more_prompt):
            line_text = line_text[len(self._more_prompt) :]

        self.append("\n")
        self._evaluate(line_text)
        return "break"  # Prevent default Tkinter newline handling

    def _evaluate(self, line: str) -> None:
        # Handle simple helper shortcuts like 'quit' or 'exit'
        if line.strip() in ("quit", "exit") and line.strip() in self.locals:
            if callable(self.locals[line.strip()]):
                self.locals[line.strip()]()
                return

        # Create streams that route REPL evaluation output directly into this widget
        repl_stdout = GuiStream(self.append, tag="stdout")
        repl_stderr = GuiStream(self.append, tag="stderr")

        old_stdout, old_stderr = sys.stdout, sys.stderr
        try:
            # Temporarily redirect standard streams during evaluation
            sys.stdout = TeeStream(old_stdout, repl_stdout)
            sys.stderr = TeeStream(old_stderr, repl_stderr)

            # push() returns True if multi-line input is incomplete (e.g., inside 'def' or 'for')
            more = self.console.push(line)
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        # Print the next prompt based on console state
        if more:
            self.append(self._more_prompt, tag="stdout")
        else:
            self.append(self._prompt, tag="stdout")