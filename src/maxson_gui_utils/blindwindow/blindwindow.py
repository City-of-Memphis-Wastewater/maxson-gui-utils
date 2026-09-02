#!/usr/bin/env python3
# src/maxson_gui_utils/blindwindow/blindwindow.py
from __future__ import annotations

import json
import logging
import socket
import sys
import threading
import pyhabitat

from maxson_gui_utils.textpane import TextPane
from .ansi import strip_ansi
from .registration import (
    IPC_HOST,
    IPC_PORT,
    PIPE_NAME,
    register_listener,
    unregister_listener,
    get_uds_path,
)
from .streams import GuiStream, TeeStream

logger = logging.getLogger(__name__)


class BlindWindow(TextPane):
    """
    Passive output display window.
    Intercepts sys.stdout/sys.stderr and subscribes to registration dispatch events.
    """

    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)

        self._orig_stdout = sys.stdout
        self._orig_stderr = sys.stderr

        # 1. Intercept raw stdout/stderr writes
        self._sys_gui_stream = GuiStream(lambda text: self.append(strip_ansi(text)))
        sys.stdout = TeeStream(self._orig_stdout, self._sys_gui_stream)
        sys.stderr = TeeStream(self._orig_stderr, self._sys_gui_stream)

        # 2. Register listener for Console() dispatch events
        register_listener(self.append)

        # 3. Cross-process IPC Receiver Setup
        self._ipc_running = True
        self._ipc_thread = threading.Thread(target=self._ipc_listen_loop, daemon=True)
        self._ipc_thread.start()

    def _ipc_listen_loop(self) -> None:
        """Routes IPC listening strategy based on target platform."""
        if sys.platform == "win32":
            self._listen_named_pipe()
        else:
            self._listen_udp()

    def _listen_named_pipe(self) -> None:
        """Windows Named Pipe Listener Loop."""
        from multiprocessing.connection import Listener

        try:
            listener = Listener(PIPE_NAME, family="AF_PIPE")
            logger.debug(f"Bound Windows Named Pipe listener at {PIPE_NAME}")
            while self._ipc_running:
                try:
                    conn = listener.accept()
                    while self._ipc_running:
                        try:
                            payload = conn.recv()
                            text = payload.get("text", "")
                            tag = payload.get("tag", "stdout")
                            clean_text = strip_ansi(text)
                            self.after(0, self.append, clean_text, tag)
                        except EOFError:
                            break
                    conn.close()
                except Exception as e:
                    logger.debug(f"Named Pipe connection error: {e}")
            listener.close()
        except Exception as e:
            logger.warning(f"Failed to bind Named Pipe IPC listener: {e}")

    def _listen_udp(self) -> None:
        """POSIX UDP Socket Listener Loop."""
        self._ipc_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._ipc_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self._ipc_socket.bind((IPC_HOST, IPC_PORT))
            logger.debug(f"Bound UDP IPC listener on {IPC_HOST}:{IPC_PORT}")
            self._ipc_socket.settimeout(1.0)
            while self._ipc_running:
                try:
                    data, _ = self._ipc_socket.recvfrom(65535)
                    if not data:
                        continue

                    payload = json.loads(data.decode("utf-8"))
                    text = payload.get("text", "")
                    tag = payload.get("tag", "stdout")

                    clean_text = strip_ansi(text)
                    self.after(0, self.append, clean_text, tag)

                except socket.timeout:
                    continue
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"Failed to bind UDP IPC server on port {IPC_PORT}: {e}")

    def _listen_uds(self) -> None:
        """POSIX UDS Listener for macOS and Linux."""
        from pathlib import Path
        uds_path = get_uds_path()
        
        if uds_path.exists():
            try:
                uds_path.unlink()
            except OSError:
                pass

        self._ipc_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        try:
            self._ipc_socket.bind(str(uds_path))
            self._ipc_socket.settimeout(1.0)
            
            while self._ipc_running:
                try:
                    data, _ = self._ipc_socket.recvfrom(65535)
                    if not data:
                        continue
                    payload = json.loads(data.decode("utf-8"))
                    text = payload.get("text", "")
                    tag = payload.get("tag", "stdout")
                    
                    clean_text = strip_ansi(text)
                    self.after(0, self.append, clean_text, tag)
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.debug(f"UDS socket read error: {e}")
        except Exception as e:
            logger.warning(f"Failed to bind UDS IPC listener at {uds_path}: {e}")
        finally:
            if uds_path.exists():
                try:
                    uds_path.unlink()
                except OSError:
                    pass

    def destroy(self):
        """Clean up process I/O streams, unregister listeners, and stop IPC thread."""
        self._ipc_running = False
        if hasattr(self, "_ipc_socket"):
            try:
                self._ipc_socket.close()
            except Exception:
                pass

        sys.stdout = self._orig_stdout
        sys.stderr = self._orig_stderr
        unregister_listener(self.append)
        super().destroy()


def start_blindwindow() -> None:
    """Launch BlindWindow as a standalone Tkinter app."""
    if not pyhabitat.tkinter_is_available():
        logger.error("BlindWindow requires Tkinter, not available in this environment.")
        return

    import tkinter as tk
    root = tk.Tk()
    root.title("BlindWindow")
    bw = BlindWindow(root)
    bw.pack(fill="both", expand=True)
    root.mainloop()


if __name__ == "__main__":
    start_blindwindow()
