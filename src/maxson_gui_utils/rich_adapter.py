#!/usr/bin/env python3
# src/maxson_gui_utils/rich_adapter.py

from rich.console import Console
from .streams import GuiStream

def make_rich_console(callback):
    """
    Create a Rich Console that writes into a TextPane.
    """
    stream = GuiStream(callback)
    return Console(file=stream, force_terminal=True, color_system="truecolor")
