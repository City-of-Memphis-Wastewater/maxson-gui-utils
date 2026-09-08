#!/usr/bin/env python3
# src/maxson_gui_utils/blindwindow/registration.py
from __future__ import annotations

import logging
import threading
from typing import Any, Callable

from .ansi import strip_ansi
from .spool import (
    SPOOL_PATH,
    decode_records_partial,
    write_record,
)

logger = logging.getLogger(__name__)

# Prevent duplicate dispatch when Console has already dispatched output.
_DISPATCH_GUARD = threading.local()

# In-process listeners, e.g. BlindWindow text panes.
_LISTENERS: list[Callable[[str, str], None]] = []

# Signals the spool listener thread to stop.
_STOP_EVENT = threading.Event()

class suppress_stream_wrapper_dispatch:
    """
    Suppress SystemStreamWrapper dispatch within this context.

    This is used when Console has already dispatched the output and the
    stream wrapper should not dispatch it a second time.
    """

    def __enter__(self) -> suppress_stream_wrapper_dispatch:
        depth = getattr(_DISPATCH_GUARD, "depth", 0)
        _DISPATCH_GUARD.depth = depth + 1
        logger.debug("[DispatchGuard] Suppress depth increased to %d", _DISPATCH_GUARD.depth)
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc_val: Any,
        exc_tb: Any,
    ) -> None:
        depth = getattr(_DISPATCH_GUARD, "depth", 1)
        _DISPATCH_GUARD.depth = max(0, depth - 1)
        logger.debug("[DispatchGuard] Suppress depth decreased to %d", _DISPATCH_GUARD.depth)


def is_dispatch_suppressed() -> bool:
    """Return whether stream-wrapper dispatch is currently suppressed."""
    return getattr(_DISPATCH_GUARD, "depth", 0) > 0


def register_listener(callback: Callable[[str, str], None]) -> None:
    """Register an in-process output listener."""
    if callback not in _LISTENERS:
        _LISTENERS.append(callback)
        logger.debug("[Registration] Registered in-process listener: %r", callback)


def unregister_listener(callback: Callable[[str, str], None]) -> None:
    """Unregister an in-process output listener."""
    if callback in _LISTENERS:
        _LISTENERS.remove(callback)
        logger.debug("[Registration] Unregistered in-process listener: %r", callback)


def dispatch_write(
    text: str,
    tag: str = "stdout",
) -> None:
    """
    Dispatch output to the BlindWindow spool.

    The spool is the canonical cross-process transport. Every process may
    append records to the same spool.

    Registered in-process listeners are notified in addition to the spool
    append; they do not replace it.
    """
    logger.debug("[Dispatch] dispatch_write invoked | tag=%s | text_repr=%r", tag, text[:60])
    clean_text = strip_ansi(text)

    if not clean_text:
        logger.debug("[Dispatch] Text empty after strip_ansi; suppressing dispatch.")
        return

    # Canonical cross-process transport.
    logger.debug("[Dispatch] Writing record to spool file.")
    write_record(clean_text, tag)

    # Notify listeners in this process as an additional convenience.
    for listener in list(_LISTENERS):
        logger.debug("[Dispatch] Notifying %d in-process listener(s).", len(_LISTENERS))
        try:
            listener(clean_text, tag)
        except Exception:
            logger.exception("In-process listener dispatch failed")


def start_spool_listener(
    callback: Callable[[str, str], None],
) -> threading.Thread:
    """
    Start a background thread that tails the BlindWindow spool.

    Returns the listener thread so the caller can retain it if desired.
    """
    _STOP_EVENT.clear()
    logger.info("[SpoolListener] Starting background spool listener thread...")

    thread = threading.Thread(
        target=_listen_spool,
        args=(callback,),
        daemon=True,
        name="BlindWindow-Spool-Listener",
    )
    thread.start()

    return thread


def _listen_spool(
    callback: Callable[[str, str], None],
) -> None:
    """Tail the append-only BlindWindow spool."""
    offset = 0
    pending = b""
    logger.debug("[SpoolListener] Tailing started on spool path: %s", SPOOL_PATH)

    while not _STOP_EVENT.is_set():
        try:
            if not SPOOL_PATH.exists():
                _STOP_EVENT.wait(0.1)
                continue

            with SPOOL_PATH.open("rb") as spool:
                spool.seek(offset)
                chunk = spool.read()

            if chunk:
                logger.debug("[SpoolListener] Read chunk of %d bytes from offset %d", len(chunk), offset)
                pending += chunk

                records, consumed = decode_records_partial(pending)

                if records:
                    logger.debug("[SpoolListener] Decoded %d record(s) from spool chunk.", len(records))

                for record in records:
                    callback(
                        record["text"],
                        record.get("tag", "stdout"),
                    )

                if consumed:
                    pending = pending[consumed:]
                    offset += consumed
                    logger.debug("[SpoolListener] Consumed %d bytes, new offset is %d", consumed, offset)

            _STOP_EVENT.wait(0.1)

        except Exception:
            logger.exception("BlindWindow spool listener failed")
            _STOP_EVENT.wait(0.5)

    logger.info("[SpoolListener] Spool listener thread stopping.")

def stop_spool_listener() -> None:
    """Request that the spool listener stop."""
    logger.info("[SpoolListener] Requesting spool listener thread stop.")
    _STOP_EVENT.set()
