#!/usr/bin/env python3
# src/maxson_gui_utils/registration.py
from __future__ import annotations

import json
import socket
from typing import Any, Callable, List

# Active in-process listeners: callback(text: str, tag: str)
_LISTENERS: List[Callable[[str, str], None]] = []

IPC_HOST = "127.0.0.1"
IPC_PORT = 9999


def register_listener(callback: Callable[[str, str], None]) -> None:
    """Registers a pane callback (e.g. TextPane.append) to receive console outputs."""
    if callback not in _LISTENERS:
        _LISTENERS.append(callback)


def unregister_listener(callback: Callable[[str, str], None]) -> None:
    """Removes a pane callback from global listeners."""
    if callback in _LISTENERS:
        _LISTENERS.remove(callback)


def dispatch_write(text: str, tag: str = "stdout") -> None:
    """Dispatches text chunks to in-process listeners and broadcasts via UDP IPC."""
    # 1. In-process dispatch
    for listener in list(_LISTENERS):
        try:
            listener(text, tag)
        except Exception:
            pass

    # 2. Cross-process UDP dispatch (fire-and-forget)
    try:
        payload = json.dumps({"text": text, "tag": tag}).encode("utf-8")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Set a zero timeout so sending never blocks execution
        sock.settimeout(0.0)
        sock.sendto(payload, (IPC_HOST, IPC_PORT))
        sock.close()
    except Exception:
        # Silently fail if port 9999 isn't bound by a receiver
        pass
