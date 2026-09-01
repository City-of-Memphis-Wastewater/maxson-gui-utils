#!/usr/bin/env python3
# src/maxson_gui_utils/console.py

from __future__ import annotations

import sys
from typing import Optional
from rich.console import Console as RichConsole

from .registration import dispatch_write
from .streams import GuiStream, TeeStream


def Console(
    stderr: bool = False,
    tag: Optional[str] = None,
    tee_sys: bool = True,
    **kwargs,
) -> RichConsole:
    """
    Drop-in replacement for rich.console.Console.
    Directs output to active maxson-gui-utils listeners with Tkinter tag metadata.
    """
    resolved_tag = tag if tag is not None else ("stderr" if stderr else "stdout")
    gui_stream = GuiStream(dispatch_write, tag=resolved_tag)

    if tee_sys:
        target_sys = sys.stderr if stderr else sys.stdout
        out_stream = TeeStream(target_sys, gui_stream) if target_sys is not None else gui_stream
    else:
        out_stream = gui_stream

    kwargs.setdefault("force_terminal", True)
    kwargs.setdefault("color_system", "truecolor")

    return RichConsole(
        file=out_stream,
        stderr=stderr,
        **kwargs,
    )