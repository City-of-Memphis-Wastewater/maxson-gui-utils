#!/usr/bin/env python3
# src/maxson_gui_utils/rich_adapter.py
from __future__ import annotations
from typing import Callable
from rich.console import Console
from .streams import GuiStream, TeeStream

def make_rich_console(
    callback: Callable[[str], None],
    stderr: bool = False,
    tee_sys: bool = True
)-> Console:
    """
    Create a Rich Console that writes into a TextPane callback.
    
    :param callback: GuiStream callback for Tkinter rendering.
    :param stderr: If True, tees or targets sys.stderr instead of sys.stdout.
    :param tee_sys: If True, duplicates output to active terminal streams (if available).
    """
    gui_stream = GuiStream(callback)

    if tee_sys:
        import sys
        # Select target system stream, falling back safely if sys.stdout/stderr is None (e.g. GUI app)
        target_sys = sys.stderr if stderr else sys.stdout
        out_stream = TeeStream(target_sys, gui_stream) if target_sys is not None else gui_stream
    else:
        out_stream = gui_stream
        
    return Console(
        file=out_stream, 
        force_terminal=True, 
        color_system="truecolor",
        stderr=stderr
    )
