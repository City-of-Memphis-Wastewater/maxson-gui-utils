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
    """
    Returns a short runtime path for POSIX Unix Domain Socket to satisfy macOS length limits.
    macOS (Darwin) AF_UNIX path limit is 104 bytes. Using /tmp directly guarantees compliance.
    """
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "maxson_gui_ipc.sock"
    base_dir = Path("/tmp") if sys.platform == "darwin" else Path(os.environ.get("XDG_RUNTIME_DIR", tempfile.gettempdir()))
    return base_dir / "mgui.sock"


def dispatch_write(
    text: str,
    tag: str = "stdout",
    *,
    port: int = IPC_PORT,
) -> None:
    """Dispatches text chunks to in-process listeners and broadcasts via cross-platform IPC."""
    clean_text = strip_ansi(text)
    if not clean_text:
        return

    # 1. In-process dispatch (prioritized for same-process UI instances)
    if _LISTENERS:
        for listener in list(_LISTENERS):
            try:
                listener(clean_text, tag)
            except Exception as e:
                logger.error("In-process listener dispatch failed: %s", e, exc_info=True)
        return

    # 2. Cross-process IPC dispatch (fire-and-forget for external subshells / CLI processes)
    payload_dict = {"text": clean_text, "tag": tag}

    if sys.platform == "win32":
        if not _send_named_pipe(payload_dict):
            _send_udp(payload_dict, port)
    else:
        if not _send_uds(payload_dict):
            _send_udp(payload_dict, port)


def _send_named_pipe(payload_dict: dict[str, str]) -> bool:
    """Windows-safe IPC using Named Pipes (bypasses Windows Firewall / MSIX warnings)."""
    try:
        from multiprocessing.connection import Client

        with Client(PIPE_NAME, family="AF_PIPE") as conn:
            conn.send(payload_dict)
        return True
    except Exception as e:
        logger.debug("Named pipe IPC connect attempt failed: %s", e)
        return False


def _send_uds(payload_dict: dict[str, str]) -> bool:
    """
    POSIX UDS Sender with 4KB chunking.
    Prevents [Errno 40] EMSGSIZE on macOS when transmitting large outputs like helptrees.
    """
    uds_path = get_uds_path()
    if not uds_path.exists():
        return False

    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        except OSError:
            pass

        text = payload_dict.get("text", "")
        tag = payload_dict.get("tag", "stdout")
        chunk_size = 4096

        encoded_text = text.encode("utf-8")
        if len(encoded_text) > chunk_size:
            for i in range(0, len(text), chunk_size):
                chunk = text[i : i + chunk_size]
                chunk_payload = json.dumps({"text": chunk, "tag": tag}).encode("utf-8")
                sock.sendto(chunk_payload, str(uds_path))
        else:
            payload = json.dumps(payload_dict).encode("utf-8")
            sock.sendto(payload, str(uds_path))

        sock.close()
        return True
    except Exception as e:
        logger.warning("UDS IPC send failed to %s: %s", uds_path, e)
        return False


def _send_udp(
    payload_dict: dict[str, str],
    port: int = IPC_PORT,
) -> None:
    """POSIX/Windows fallback IPC using blocking UDP loopback socket."""
    try:
        payload = json.dumps(payload_dict).encode("utf-8")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Note: Avoid sock.settimeout(0.0) here to prevent BlockingIOError drops under heavy output bursts
        sock.sendto(payload, (IPC_HOST, port))
        sock.close()
    except Exception as e:
        logger.error("UDP IPC dispatch failed to %s:%d: %s", IPC_HOST, port, e, exc_info=True)


# ---- Server / Listener Background Services ----


def start_ipc_listener(
    callback: Callable[[str, str], None],
    port: Optional[int] = None,
    pipe_name: Optional[str] = None,
) -> None:
    """
    Starts the IPC listener and blocks until the transport is bound and listening.
    Spawns background daemon thread(s) listening for cross-process IPC output chunks.
    """
    _IPC_STOP_EVENT.clear()
    target_port = port if port is not None else IPC_PORT
    target_pipe = pipe_name if pipe_name is not None else PIPE_NAME

    ready = threading.Event()
    error: list[BaseException] = []

    if sys.platform == "win32":
        t_pipe = threading.Thread(
            target=_listen_named_pipe,
            args=(callback, target_pipe, ready, error),
            daemon=True,
            name="IPC-NamedPipe-Listener",
        )
        t_pipe.start()
        _IPC_SERVER_THREADS.append(t_pipe)

        t_udp = threading.Thread(
            target=_listen_udp,
            args=(callback, target_port, ready, error),
            daemon=True,
            name="IPC-UDP-Listener",
        )
        t_udp.start()
        _IPC_SERVER_THREADS.append(t_udp)
    else:
        t_posix = threading.Thread(
            target=_listen_posix_ipc,
            args=(callback, target_port, ready, error),
            daemon=True,
            name="IPC-POSIX-Listener",
        )
        t_posix.start()
        _IPC_SERVER_THREADS.append(t_posix)

    if not ready.wait(timeout=5.0):
        logger.error("IPC listener timeout reached during startup.")
        raise RuntimeError("IPC listener failed to become ready within timeout.")
    if error:
        raise RuntimeError("IPC listener failed to start") from error[0]


def stop_ipc_listener() -> None:
    """Signals all active background IPC listener threads to terminate and cleans up sockets."""
    _IPC_STOP_EVENT.set()

    with _SOCKET_LOCK:
        for sock in _ACTIVE_SOCKETS:
            try:
                sock.close()
            except Exception as e:
                logger.error("IPC listener termination error: %s", e)
        _ACTIVE_SOCKETS.clear()

    uds_path = get_uds_path()
    if uds_path.exists():
        try:
            uds_path.unlink()
        except OSError as e:
            logger.debug("Failed to unlink socket at %s: %s", uds_path, e)


def _listen_named_pipe(
    callback: Callable[[str, str], None],
    pipe_name: str,
    ready: threading.Event,
    error: list[BaseException],
) -> None:
    """Windows Named Pipe Listener Loop."""
    from multiprocessing.connection import Listener

    try:
        listener = Listener(pipe_name, family="AF_PIPE")
        ready.set()
        while not _IPC_STOP_EVENT.is_set():
            try:
                conn = listener.accept()
                while not _IPC_STOP_EVENT.is_set():
                    try:
                        data = conn.recv()
                        if isinstance(data, dict) and "text" in data:
                            callback(data["text"], data.get("tag", "stdout"))
                    except EOFError:
                        break
                conn.close()
            except Exception as e:
                logger.error("Named pipe accept error: %s", e, exc_info=True)
        listener.close()
    except Exception as e:
        error.append(e)
        ready.set()


def _listen_posix_ipc(
    callback: Callable[[str, str], None],
    port: int,
    ready: threading.Event,
    error: list[BaseException],
) -> None:
    """POSIX Listener Loop: Binds Unix Domain Socket first, falls back to UDP loopback."""
    uds_path = get_uds_path()
    if uds_path.exists():
        try:
            uds_path.unlink()
        except OSError as e:
            logger.debug("Could not remove stale UDS %s: %s", uds_path, e)

    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        sock.settimeout(1.0)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        except OSError:
            pass

        sock.bind(str(uds_path))

        with _SOCKET_LOCK:
            _ACTIVE_SOCKETS.append(sock)
        logger.info("IPC UDS listener bound and ready: %s", uds_path)
        ready.set()

        try:
            while not _IPC_STOP_EVENT.is_set():
                try:
                    data, _ = sock.recvfrom(65536)
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error("UDS socket receive error: %s", e)
                    continue

                try:
                    payload = json.loads(data.decode("utf-8"))
                    if isinstance(payload, dict) and "text" in payload:
                        callback(payload["text"], payload.get("tag", "stdout"))
                except json.JSONDecodeError as e:
                    logger.warning("Invalid JSON payload on UDS socket: %s", e)

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
    except Exception as e:
        logger.warning("UDS listener binding failed (%s). Falling back to UDP loopback on port %d.", e, port)
        # Fall back to UDP loopback without populating error list unless UDP binding fails
        _listen_udp(callback, port, ready, error)


def _listen_udp(
    callback: Callable[[str, str], None],
    port: int,
    ready: threading.Event,
    error: list[BaseException],
) -> None:
    """UDP Loopback Listener Loop."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(1.0)
        sock.bind((IPC_HOST, port))

        with _SOCKET_LOCK:
            _ACTIVE_SOCKETS.append(sock)
        logger.info("IPC UDP listener ready on %s:%d", IPC_HOST, port)
        ready.set()

        try:
            while not _IPC_STOP_EVENT.is_set():
                try:
                    data, _ = sock.recvfrom(65536)
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error("UDP socket receive error: %s", e)
                    continue

                try:
                    payload = json.loads(data.decode("utf-8"))
                    if isinstance(payload, dict) and "text" in payload:
                        callback(payload["text"], payload.get("tag", "stdout"))
                except json.JSONDecodeError as e:
                    logger.warning("Invalid JSON payload on UDP socket: %s", e)

        finally:
            with _SOCKET_LOCK:
                if sock in _ACTIVE_SOCKETS:
                    _ACTIVE_SOCKETS.remove(sock)
            sock.close()
    except Exception as e:
        logger.error("Fatal error starting UDP listener on port %d: %s", port, e, exc_info=True)
        error.append(e)
        ready.set()