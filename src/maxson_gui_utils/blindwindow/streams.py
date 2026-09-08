#!/usr/bin/env python3
# src/maxson_gui_utils/blindwindow/streams.py
from __future__ import annotations

import logging
import sys
from typing import Any, Callable

from .ansi import strip_ansi
from .registration import dispatch_write, is_dispatch_suppressed

logger = logging.getLogger(__name__)


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
            logger.debug("[GuiStream.write] Forwarding %d chars to callback", len(text))
            self.callback(text, *self.args, **self.kwargs)
        return len(text)

    def flush(self) -> None:
        pass


class TeeStream:
    """Duplicates writes across multiple streams."""

    def __init__(self, *streams: Any):
        self.streams = [s for s in streams if s is not None]

    def write(self, text: str) -> int:
        for s in self.streams:
            is_tty = getattr(s, "isatty", lambda: False)()
            # Do not drop text for GuiStream instances
            is_gui = isinstance(s, GuiStream)
            output_text = text if (is_tty or is_gui) else strip_ansi(text)
            if output_text:
                logger.debug("[TeeStream.write] Writing %d chars to stream target: %r", len(output_text), s)
                s.write(output_text)
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

    def write(self, text: str) -> int:
        res = 0
        if self.target:
            res = self.target.write(text)
            if hasattr(self.target, "flush"):
                self.target.flush()

        suppressed = is_dispatch_suppressed()
        logger.debug(
            "[SystemStreamWrapper.write] tag=%s | text_len=%d | suppressed=%s",
            self.tag,
            len(text),
            suppressed,
        )

        if not suppressed:
            dispatch_write(text, tag=self.tag)

        return res

    def flush(self) -> None:
        if self.target and hasattr(self.target, "flush"):
            self.target.flush()

    def isatty(self) -> bool:
        return getattr(self.target, "isatty", lambda: False)()


def install_stream_wrappers() -> None:
    """Redirect process-level sys.stdout and sys.stderr to broadcast via dispatch_write."""
    logger.info("[StreamWrappers] Installing process-level stream wrappers...")
    if not isinstance(sys.stdout, SystemStreamWrapper):
        sys.stdout = SystemStreamWrapper(sys.stdout, tag="stdout")
        logger.debug("[StreamWrappers] sys.stdout wrapped.")
    if not isinstance(sys.stderr, SystemStreamWrapper):
        sys.stderr = SystemStreamWrapper(sys.stderr, tag="stderr")
        logger.debug("[StreamWrappers] sys.stderr wrapped.")