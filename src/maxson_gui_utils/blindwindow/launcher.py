# src/maxson_gui_utils/blindwindow/launcher.py
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

from .registration import (
    start_spool_listener,
    stop_spool_listener,
)
from .spool import clear_spool, get_spool_path, set_spool_path

logger = logging.getLogger(__name__)


def launch_blindwindow(
    title: str = "BlindWindow Output",
    always_on_top: bool = False,
    autoscroll: bool = True,
    spool_path: Optional[Path | str] = None,
    clear_on_launch: bool = True,
) -> None:
    """
    Launch the BlindWindow Tkinter interface and tail the active spool file.

    Parameters
    ----------
    title : str
        Window title string.
    always_on_top : bool
        Keep window atop other windows if True.
    autoscroll : bool
        Auto-scroll text pane on new text arrival.
    spool_path : Path or str, optional
        Explicit path override for the binary JSON spool file.
        If omitted, defaults to environment/MSIX auto-resolved path.
    clear_on_launch : bool
        If True, unlinks/clears existing spool content on startup.
    """
    import pyhabitat

    if not pyhabitat.tkinter_is_available():
        logger.error(
            "Cannot launch BlindWindow: Tkinter is not available "
            "in this Python environment."
        )
        sys.exit(1)

    import tkinter as tk

    from .blindwindow import BlindWindow

    # 1. Resolve and mutate spool path if explicitly provided
    if spool_path is not None:
        target_spool = set_spool_path(spool_path)
    else:
        target_spool = get_spool_path()

    logger.debug("[Launcher] Active spool target: %s", target_spool)

    # 2. Reset spool file state on fresh launch
    if clear_on_launch:
        logger.info("[Launcher] Clearing stale spool file at %s...", target_spool)
        clear_spool(target_spool)

    # 3. Initialize Tkinter root window
    try:
        root = tk.Tk()
    except tk.TclError as err:
        logger.error(
            "Cannot launch BlindWindow UI: No display found (%s)",
            err,
        )
        sys.exit(1)

    root.title(title)

    if always_on_top:
        root.attributes("-topmost", True)

    app = BlindWindow(
        master=root,
        autoscroll=autoscroll,
    )
    app.pack(fill="both", expand=True)

    # 4. Attach spool tailing thread directly to BlindWindow's thread-safe logging handler
    logger.info("[Launcher] Starting spool tailing listener thread...")
    start_spool_listener(app._safe_append, spool_path=target_spool)

    def _on_close() -> None:
        logger.info("[Launcher] Closing BlindWindow interface...")
        stop_spool_listener()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)

    logger.info("BlindWindow interface initialized successfully (Spool: %s).", target_spool)

    def _heartbeat():
        logger.debug("[Heartbeat] Tkinter mainloop tick")
        root.after(3000, _heartbeat)
    root.after(3000, _heartbeat)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        logger.info("BlindWindow closed via KeyboardInterrupt.")
    finally:
        stop_spool_listener()




if __name__ == "__main__":
    launch_blindwindow()