#!/usr/bin/env python3
# src/maxson_gui_utils/console.py

from __future__ import annotations

import logging
import sys
from typing import Any, Optional
from rich.console import Console as RichConsole

from .registration import dispatch_write
from .streams import GuiStream, TeeStream

logger = logging.getLogger(__name__)


class DebugConsole(RichConsole):
    """
    Subclass of rich.console.Console that intercepts prints and writes
    with debug logging before forwarding to streams and dispatch listeners.
    """

    def print(self, *objects: Any, **kwargs: Any) -> None:
        logger.debug(f"[Console.print] Printing {len(objects)} object(s)")
        super().print(*objects, **kwargs)

    def log(self, *objects: Any, **kwargs: Any) -> None:
        logger.debug(f"[Console.log] Logging {len(objects)} object(s)")
        super().log(*objects, **kwargs)


def Console(
    stderr: bool = False,
    tag: Optional[str] = None,
    tee_sys: bool = True,
    debug_stream: bool = False,
    **kwargs: Any,
) -> RichConsole:
    """
    Drop-in replacement factory for rich.console.Console.
    Directs output to active maxson-gui-utils listeners with Tkinter tag metadata.
    """
    resolved_tag = tag if tag is not None else ("stderr" if stderr else "stdout")

    def _debug_dispatch(text: str, tag_val: str = resolved_tag) -> None:
        if debug_stream:
            logger.debug(f"[Stream Dispatch] tag={tag_val} | bytes={len(text)} | text={text!r}")
        dispatch_write(text, tag=tag_val)

    gui_stream = GuiStream(_debug_dispatch, tag=resolved_tag)

    if tee_sys:
        target_sys = sys.stderr if stderr else sys.stdout
        out_stream = TeeStream(target_sys, gui_stream) if target_sys is not None else gui_stream
    else:
        out_stream = gui_stream

    kwargs.setdefault("force_terminal", True)
    kwargs.setdefault("color_system", "truecolor")

    return DebugConsole(
        file=out_stream,
        stderr=stderr,
        **kwargs,
    )
