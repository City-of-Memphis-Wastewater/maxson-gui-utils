#!/usr/bin/env python3
# src/maxson_gui_utils/blindwindow/registration.py
from __future__ import annotations

import json
import logging
import os
import socket
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any, Callable, List, Optional

from .ansi import strip_ansi
from .spool import write_record as write_record_to_spool
from .transport import IPCTransport

logger = logging.getLogger(__name__)

_DISPATCH_GUARD = threading.local()

# Active in-process listeners: callback(text: str, tag: str)
_LISTENERS: List[Callable[[str, str], None]] = []
_IPC_SERVER_THREADS: List[threading.Thread] = []

# Shutdown flag and socket registry for graceful IPC cleanup
_IPC_STOP_EVENT = threading.Event()
_ACTIVE_SOCKETS: List[socket.socket] = []
_SOCKET_LOCK = threading.Lock()

# Centralized Constants
IPC_HOST = "127.0.0.1"
IPC_PORT = int(os.environ.get("MGUI_IPC_PORT", "9999"))
PIPE_NAME = r"\\.\pipe\maxson_gui_utils_ipc"


class suppress_stream_wrapper_dispatch:
    """
    Context manager to suppress SystemStreamWrapper dispatch when Console already dispatched.
    Behavioral scope control block; PEP8 PascalCase intentionally avoided for context manager naming.
    """

    def __enter__(self) -> suppress_stream_wrapper_dispatch:
        depth = getattr(_DISPATCH_GUARD, "depth", 0)
        _DISPATCH_GUARD.depth = depth + 1
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        depth = getattr(_DISPATCH_GUARD, "depth", 1)
        _DISPATCH_GUARD.depth = max(0, depth - 1)

# keep for spool?
def is_dispatch_suppressed() -> bool:
    """Returns True if stream wrapper dispatching is currently suppressed within context."""
    return getattr(_DISPATCH_GUARD, "depth", 0) > 0

# keep for spool?
def register_listener(callback: Callable[[str, str], None]) -> None:
    """Registers a pane callback (e.g. TextPane.append) to receive console outputs."""
    if callback not in _LISTENERS:
        _LISTENERS.append(callback)

# keep for spool?
def unregister_listener(callback: Callable[[str, str], None]) -> None:
    """Removes a pane callback from global listeners."""
    if callback in _LISTENERS:
        _LISTENERS.remove(callback)


# ---- Runtime Path Generators & Inter-Process Communication Helpers ----

# replaced
def dispatch_write(
    text: str,
    tag: str = "stdout",
    *,
    transport: IPCTransport = IPCTransport.SPOOL_FILE,
) -> None:
    """Dispatch output to the local BlindWindow spool."""

    clean_text = strip_ansi(text)

    if not clean_text:
        return

    # Same-process listeners remain useful.
    if _LISTENERS:
        for listener in list(_LISTENERS):
            try:
                listener(clean_text, tag)
            except Exception as e:
                logger.error(
                    "In-process listener dispatch failed: %s",
                    e,
                    exc_info=True,
                )
        return

    # Cross-process transport: spool only.
    if transport is IPCTransport.SPOOL_FILE:
        write_record_to_spool(clean_text, tag)

# ---- Server / Listener Background Services ----

def start_ipc_listener(
    callback: Callable[[str, str], None],
    transport: IPCTransport = IPCTransport.SPOOL_FILE,
) -> None:
    """Start the selected BlindWindow transport listener."""

    _IPC_STOP_EVENT.clear()

    if transport is IPCTransport.SPOOL_FILE:
        start_spool_listener(callback)
        return

    raise ValueError(
        f"Unsupported transport: {transport}"
    )

def stop_ipc_listener() -> None:
    """Stop the BlindWindow spool listener."""

    _IPC_STOP_EVENT.set()

# in
def _listen_spool(
    callback: Callable[[str, str], None],
    port: int,
    ready: threading.Event,
    error: list[BaseException],
) -> None:
    pass
