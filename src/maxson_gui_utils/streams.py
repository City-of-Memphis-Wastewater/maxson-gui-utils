#!/usr/bin/env python3
# src/maxson_gui_utils/streams.py
from __future__ import annotations
from typing import Callable, Optional, Any

class GuiStream:
    """
    File-like stream wrapper that routes write() calls to a callable.
    Passes optional positional and keyword arguments through to the callback.
    """

    def __init__(self, callback: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        self.callback = callback
        self.args = args
        self.kwargs = kwargs

    def write(self, text: str) -> int:
        if text:
            self.callback(text, *self.args, **self.kwargs)
        return len(text)

    def flush(self) -> None:
        pass


class TeeStream:
    """
    Duplicates write() calls across multiple valid streams.
    Ignores None streams (e.g. unattached sys.stdout in GUI mode).
    """

    def __init__(self, *streams: Any):
        self.streams = [s for s in streams if s is not None]

    def write(self, text: str) -> int:
        for s in self.streams:
            s.write(text)
        return len(text)

    def flush(self) -> None:
        for s in self.streams:
            if hasattr(s, "flush"):
                s.flush()