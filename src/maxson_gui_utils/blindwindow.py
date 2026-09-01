#!/usr/bin/env python3
# src/maxson_gui_utils/blindwindow.py
from __future__ import annotations
import sys
import logging
import pyhabitat
import socket
import threading
import json

from .textpane import TextPane
from .streams import GuiStream, TeeStream
from .ansi import strip_ansi
from .registration import IPC_HOST, IPC_PORT, register_listener, unregister_listener

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
        #self._listener_cb = lambda text: self.append(strip_ansi(text))
        #register_listener(self._listener_cb)
        register_listener(self.append)
        logger.debug("register_listener()")

        # 3. Cross-process UDP IPC Receiver Setup
        self._ipc_running = True
        self._ipc_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Allow immediate socket reuse across app restarts
        self._ipc_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self._ipc_socket.bind((IPC_HOST, IPC_PORT))
            self._ipc_thread = threading.Thread(
                target=self._udp_listen_loop, daemon=True
            )
            self._ipc_thread.start()
        except Exception as e:
            logger.warning(f"Failed to bind UDP IPC server on port {IPC_PORT}: {e}")

    def _udp_listen_loop(self) -> None:
        """Background thread listening for datagram payloads."""
        self._ipc_socket.settimeout(1.0)
        while self._ipc_running:
            try:
                data, _ = self._ipc_socket.recvfrom(65535)
                if not data:
                    continue
                
                payload = json.loads(data.decode("utf-8"))
                text = payload.get("text", "")
                tag = payload.get("tag", "stdout")

                logger.debug(f"[BlindWindow UDP Recv] tag={tag} | bytes={len(text)}")
                
                # Thread safety: Schedule write execution on Tkinter's main UI thread
                self.after(0, self.append, text, tag)
            except socket.timeout:
                continue
            except Exception:
                continue
                
    def destroy(self):
        """Clean up process I/O streams, unregister listeners, and stop UDP thread."""
        self._ipc_running = False
        try:
            self._ipc_socket.close()
        except Exception:
            pass

        sys.stdout = self._orig_stdout
        sys.stderr = self._orig_stderr
        #unregister_listener(self._listener_cb)
        unregister_listener(self.append)
        logger.debug("unregister_listener()")
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
