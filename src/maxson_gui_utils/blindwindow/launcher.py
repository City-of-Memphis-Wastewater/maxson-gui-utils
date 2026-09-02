# src/maxson_gui_utils/blindwindow/launcher.py
from __future__ import annotations

import logging
import sys
from typing import Optional

from .registration import register_listener, start_ipc_listener

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
    def _in_process_receiver(text: str, tag: str = "stdout") -> None:
        root.after_idle(lambda: app.append(text, tag=tag))

    register_listener(_in_process_receiver)

    # 5. Spin up cross-process IPC socket/pipe server
    start_ipc_listener(
        callback=_in_process_receiver,
        port=port,
        pipe_name=pipe_name,
    )

    def _on_close() -> None:
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)

    logger.debug(f"BlindWindow launched with title='{title}', port={port}, pipe={pipe_name}")

    # 6. Hand control over to Tkinter event loop
    try:
        root.mainloop()
    except KeyboardInterrupt:
        logger.info("BlindWindow closed via KeyboardInterrupt.")