#!/usr/bin/env python3
# src/maxson_gui_utils/registration.py
from __future__ import annotations

import json
import logging
import os
import socket
import sys
import threading
from pathlib import Path
from typing import Any, Callable, List, Optional

from .ansi import strip_ansi

logger = logging.getLogger(__name__)

_DISPATCH_GUARD = threading.local()

# Active in-process listeners: callback(text: str, tag: str)
_LISTENERS: List[Callable[[str, str], None]] = []
_IPC_SERVER_THREADS: List[threading.Thread] = []

# Shutdown flag and socket registry for graceful IPC cleanup
_IPC_STOP_EVENT = threading.Event()
_ACTIVE_SOCKETS: List[socket.socket] = []
_SOCKET_LOCK = threading.Lock()

IPC_HOST = "127.0.0.1"
IPC_PORT = 9999
PIPE_NAME = r"\\.\pipe\maxson_gui_utils_ipc"


class suppress_stream_wrapper_dispatch:
    """
    Context manager to suppress SystemStreamWrapper dispatch when Console already dispatched.
    Behavioral scope control block, ergo PEP8 PascalCase is not used.
    """

    def __enter__(self) -> suppress_stream_wrapper_dispatch:
        depth = getattr(_DISPATCH_GUARD, "depth", 0)
        _DISPATCH_GUARD.depth = depth + 1
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        depth = getattr(_DISPATCH_GUARD, "depth", 1)
        _DISPATCH_GUARD.depth = max(0, depth - 1)


def is_dispatch_suppressed() -> bool:
    """Returns True if stream wrapper dispatching is currently suppressed within context."""
    return getattr(_DISPATCH_GUARD, "depth", 0) > 0


def register_listener(callback: Callable[[str, str], None]) -> None:
    """Registers a pane callback (e.g. TextPane.append) to receive console outputs."""
    if callback not in _LISTENERS:
        _LISTENERS.append(callback)


def unregister_listener(callback: Callable[[str, str], None]) -> None:
    """Removes a pane callback from global listeners."""
    if callback in _LISTENERS:
        _LISTENERS.remove(callback)


# ---- Runtime Path Generators & Inter-Process Communication Helpers ----


def get_uds_path() -> Path:
    """Returns a cross-platform user runtime directory for Unix Domain Socket if needed."""
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "maxson_gui_ipc.sock"
    return Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / "maxson_gui_ipc.sock"


def dispatch_write(text: str, tag: str = "stdout") -> None:
    """Dispatches text chunks to in-process listeners and broadcasts via cross-platform IPC."""

    # 0. Always clean text before dispatching to listeners/IPC
    clean_text = strip_ansi(text)
    if not clean_text:
        return 
    
    # 1. In-process dispatch
    if _LISTENERS:
        for listener in list(_LISTENERS):
            try:
                listener(clean_text, tag)
            except Exception:
                pass
        # Skip IPC broadcast if an in-process listener processed the write locally
        return

    # 2. Cross-process IPC dispatch (fire-and-forget for external subshells / CLI processes)
    payload_dict = {"text": clean_text, "tag": tag}

    # If running on native Windows (non-WSL), try Named Pipe first; fall back to UDP loopback
    if sys.platform == "win32":
        if not _send_named_pipe(payload_dict):
            _send_udp(payload_dict)
    else:
        # Try Unix Domain Socket first (macOS / Linux); fall back to UDP loopback
        if not _send_uds(payload_dict):
            _send_udp(payload_dict)


def _send_named_pipe(payload_dict: dict[str, str]) -> bool:
    """Windows-safe IPC using Named Pipes (bypasses Windows Firewall / MSIX warnings)."""
    try:
        from multiprocessing.connection import Client

        with Client(PIPE_NAME, family="AF_PIPE") as conn:
            conn.send(payload_dict)
        return True
    except Exception:
        # Listener (BlindWindow) is not active or pipe is non-existent
        return False


def _send_uds(payload_dict: dict[str, str]) -> bool:
    """POSIX IPC via Unix Domain Socket (macOS / Linux)."""
    uds_path = get_uds_path()
    if not uds_path.exists():
        return False
    try:
        payload = json.dumps(payload_dict).encode("utf-8")
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        sock.sendto(payload, str(uds_path))
        sock.close()
        return True
    except Exception:
        return False


def _send_udp(payload_dict: dict[str, str]) -> None:
    """POSIX/Windows fallback IPC using UDP loopback socket."""
    try:
        payload = json.dumps(payload_dict).encode("utf-8")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.0)
        sock.sendto(payload, (IPC_HOST, IPC_PORT))
        sock.close()
    except Exception:
        pass


# ---- Server / Listener Background Services ----


def start_ipc_listener(
    callback: Callable[[str, str], None],
    port: Optional[int] = None,
    pipe_name: Optional[str] = None,
) -> None:
    """
    Spawns background daemon thread(s) listening for cross-process IPC output chunks.
    Routes received payload dicts ({"text": ..., "tag": ...}) to the provided callback.
    """
    _IPC_STOP_EVENT.clear()
    target_port = port if port is not None else IPC_PORT
    target_pipe = pipe_name if pipe_name is not None else PIPE_NAME

    if sys.platform == "win32":
        t_pipe = threading.Thread(
            target=_listen_named_pipe,
            args=(callback, target_pipe),
            daemon=True,
            name="IPC-NamedPipe-Listener",
        )
        t_pipe.start()
        _IPC_SERVER_THREADS.append(t_pipe)

        t_udp = threading.Thread(
            target=_listen_udp,
            args=(callback, target_port),
            daemon=True,
            name="IPC-UDP-Listener",
        )
        t_udp.start()
        _IPC_SERVER_THREADS.append(t_udp)
    else:
        # On POSIX systems, spawn UDS listener with automatic fallback to UDP if socket binding fails
        t_posix = threading.Thread(
            target=_listen_posix_ipc,
            args=(callback, target_port),
            daemon=True,
            name="IPC-POSIX-Listener",
        )
        t_posix.start()
        _IPC_SERVER_THREADS.append(t_posix)


def stop_ipc_listener() -> None:
    """Signals all active background IPC listener threads to terminate and cleans up sockets."""
    _IPC_STOP_EVENT.set()
    
    with _SOCKET_LOCK:
        for sock in _ACTIVE_SOCKETS:
            try:
                sock.close()
            except Exception:
                pass
        _ACTIVE_SOCKETS.clear()

    uds_path = get_uds_path()
    if uds_path.exists():
        try:
            uds_path.unlink()
        except OSError:
            pass


def _listen_named_pipe(callback: Callable[[str, str], None], pipe_name: str) -> None:
    """Windows Named Pipe Listener Loop."""
    from multiprocessing.connection import Listener

    try:
        listener = Listener(pipe_name, family="AF_PIPE")
        while not _IPC_STOP_EVENT.is_set():
            try:
                conn = listener.accept()
                while not _IPC_STOP_EVENT.is_set():
                    try:
                        data = conn.recv()
                        if isinstance(data, dict) and "text" in data:
                            #callback(data["text"], data.get("tag", "stdout"))
                            text = data["text"]
                            tag = data.get("tag", "stdout")
                            callback(text, tag)
                    except EOFError:
                        break
                conn.close()
            except Exception:
                pass
        listener.close()
    except Exception:
        pass


def _listen_posix_ipc(callback: Callable[[str, str], None], port: int) -> None:
    """POSIX Listener Loop: Binds Unix Domain Socket first, falls back to UDP loopback."""
    uds_path = get_uds_path()
    if uds_path.exists():
        try:
            uds_path.unlink()
        except OSError:
            pass

    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        sock.settimeout(1.0)
        sock.bind(str(uds_path))

        with _SOCKET_LOCK:
            _ACTIVE_SOCKETS.append(sock)

        try:
            while not _IPC_STOP_EVENT.is_set():
                try:
                    data, _ = sock.recvfrom(65536)
                    if data:
                        payload = json.loads(data.decode("utf-8"))
                        if isinstance(payload, dict) and "text" in payload:
                            text = payload["text"]
                            tag = payload.get("tag", "stdout")
                            callback(text, tag)
                except socket.timeout:
                    continue
                except Exception:
                    pass
        finally:
            with _SOCKET_LOCK:
                if sock in _ACTIVE_SOCKETS:
                    _ACTIVE_SOCKETS.remove(sock)
            sock.close()
            if uds_path.exists():
                try:
                    uds_path.unlink()
                except OSError:
                    pass
    except Exception:
        # Fallback to UDP listener loop if UDS socket creation or binding fails
        _listen_udp(callback, port)


def _listen_udp(callback: Callable[[str, str], None], port: int) -> None:
    """UDP Loopback Listener Loop."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(1.0)
        sock.bind((IPC_HOST, port))

        with _SOCKET_LOCK:
            _ACTIVE_SOCKETS.append(sock)

        try:
            while not _IPC_STOP_EVENT.is_set():
                try:
                    data, _ = sock.recvfrom(65536)
                    if data:
                        payload = json.loads(data.decode("utf-8"))
                        if isinstance(payload, dict) and "text" in payload:
                            text = payload["text"]
                            tag = payload.get("tag", "stdout")
                            callback(text, tag)
                except socket.timeout:
                    continue
                except Exception:
                    pass
        finally:
            with _SOCKET_LOCK:
                if sock in _ACTIVE_SOCKETS:
                    _ACTIVE_SOCKETS.remove(sock)
            sock.close()
    except Exception:
        pass