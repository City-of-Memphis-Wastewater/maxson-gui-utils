#!/usr/bin/env python3
# src/maxson_gui_utils/streams.py
from __future__ import annotations
from typing import Callable, Optional, Any
import sys
from .registration import dispatch_write, is_dispatch_suppressed

"""
For external CLI tools like pdflinkcheck running in another terminal window, 
set PYTHONUNBUFFERED=1 in your shell environment 
or add install_stream_wrappers() at the entry point of those tools to guarantee real-time dispatching.
"""
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

class SystemStreamWrapper:
    """Wraps process-level sys.stdout or sys.stderr to route writes through dispatch_write."""

    def __init__(self, target: Any, tag: str = "stdout") -> None:
        self.target = target
        self.tag = tag

    def write_defunct(self, text: str) -> int:
        res = len(text)
        if self.target:
            res = self.target.write(text)
            if hasattr(self.target, "flush"):
                self.target.flush()
        dispatch_write(text, tag=self.tag)
        return res
    
    def write(self, text: str) -> int:
        res = 0
        if self.target:
            res = self.target.write(text)
            if hasattr(self.target, "flush"):
                self.target.flush()
        
        # Only dispatch if this write didn't originate from our Console stream guard
        if not is_dispatch_suppressed():
            dispatch_write(text, tag=self.tag)
            
        return res
    def flush(self) -> None:
        if self.target and hasattr(self.target, "flush"):
            self.target.flush()

    def isatty(self) -> bool:
        return getattr(self.target, "isatty", lambda: False)()
    
def install_stream_wrappers() -> None:
    """Redirect process-level sys.stdout and sys.stderr to broadcast via dispatch_write."""
    if not isinstance(sys.stdout, SystemStreamWrapper):
        sys.stdout = SystemStreamWrapper(sys.stdout, tag="stdout")
    if not isinstance(sys.stderr, SystemStreamWrapper):
        sys.stderr = SystemStreamWrapper(sys.stderr, tag="stderr")

