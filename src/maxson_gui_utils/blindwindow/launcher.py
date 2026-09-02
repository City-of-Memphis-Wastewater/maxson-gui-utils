# src/maxson_gui_utils/blindwindow/launcher.py
from __future__ import annotations

import logging
import sys
from typing import Optional

from .registration import register_listener, start_ipc_listener, stop_ipc_listener

logger = logging.getLogger(__name__)


def launch_blindwindow(
    title: str = "BlindWindow Output",
    port: Optional[int] = None,
    pipe_name: Optional[str] = None,
    always_on_top: bool = False,
    autoscroll: bool = True,
) -> None:
    """
    Instantiates and starts the BlindWindow Tkinter interface and
    attaches stream listeners across in-process dispatches and IPC sockets.
    """
    import pyhabitat

    if not pyhabitat.tkinter_is_available():
        logger.error("Cannot launch BlindWindow: Tkinter is not available in this Python environment.")
        sys.exit(1)

    import tkinter as tk
    from .blindwindow import BlindWindow
    # 1. Guard against headless environments without a display server
    try:
        root = tk.Tk()
    except tk.TclError as err:
        logger.error(f"Cannot launch BlindWindow UI: No display found ({err})")
        sys.exit(1)

    # 2. Window configuration & state flags
    root.title(title)
    if always_on_top:
        root.attributes("-topmost", True)

    # 3. Instantiate the core TextPane / UI container
    app = BlindWindow(master=root, autoscroll=autoscroll)
    app.pack(fill="both", expand=True)

    # 4. Attach local in-process dispatch listener
    def _receiver(text: str, tag: str = "stdout") -> None:
        root.after_idle(lambda: app.append(text, tag=tag))

    register_listener(_receiver)

    

    # 5. Spin up cross-process IPC socket/pipe server
    try:
        start_ipc_listener(
            callback=_receiver,
            port=port,
            pipe_name=pipe_name,
        )
    except RuntimeError as err:
        logger.critical("Failed to initialize BlindWindow IPC server: %s", err)
        root.destroy()
        sys.exit(1)

    def _on_close() -> None:
        stop_ipc_listener()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)
    logger.info("BlindWindow interface initialized successfully.")
    
    # 6. Hand control over to Tkinter event loop
    try:
        root.mainloop()
    except KeyboardInterrupt:
        logger.info("BlindWindow closed via KeyboardInterrupt.")

if __name__ == "__main__":
    launch_blindwindow()