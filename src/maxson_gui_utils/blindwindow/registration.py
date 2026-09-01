#!/usr/bin/env python3
# src/maxson_gui_utils/registration.py
from __future__ import annotations
import sys
import json
import socket
from typing import Any, Callable, List

# Active in-process listeners: callback(text: str, tag: str)
_LISTENERS: List[Callable[[str, str], None]] = []

IPC_HOST = "127.0.0.1"
IPC_PORT = 9999
PIPE_NAME = r"\\.\pipe\maxson_gui_utils_ipc"

def register_listener(callback: Callable[[str, str], None]) -> None:
    """Registers a pane callback (e.g. TextPane.append) to receive console outputs."""
    if callback not in _LISTENERS:
        _LISTENERS.append(callback)


def unregister_listener(callback: Callable[[str, str], None]) -> None:
    """Removes a pane callback from global listeners."""
    if callback in _LISTENERS:
        _LISTENERS.remove(callback)

# ----

def dispatch_write(text: str, tag: str = "stdout") -> None:
    """Dispatches text chunks to in-process listeners and broadcasts via cross-platform IPC."""
    # 1. In-process dispatch
    for listener in list(_LISTENERS):
        try:
            listener(text, tag)
        except Exception:
            pass

    # 2. Cross-process IPC dispatch (fire-and-forget)
    payload_dict = {"text": text, "tag": tag}

    if sys.platform == "win32":
        _send_named_pipe(payload_dict)
    else:
        _send_udp(payload_dict)


def _send_named_pipe(payload_dict: dict) -> None:
    """Windows-safe IPC using Named Pipes (bypasses Windows Firewall / MSIX warnings)."""
    try:
        from multiprocessing.connection import Client

        with Client(PIPE_NAME, family="AF_PIPE") as conn:
            conn.send(payload_dict)
    except Exception:
        # Listener (BlindWindow) is not active or pipe non-existent
        pass


def _send_udp(payload_dict: dict) -> None:
    """POSIX IPC using UDP loopback socket."""
    try:
        payload = json.dumps(payload_dict).encode("utf-8")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.0)
        sock.sendto(payload, (IPC_HOST, IPC_PORT))
        sock.close()
    except Exception:
        pass

# ----
