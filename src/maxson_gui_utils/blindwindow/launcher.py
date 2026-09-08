# src/maxson_gui_utils/blindwindow/launcher.py
from __future__ import annotations

import logging
import sys

from .registration import (
    register_listener,
    start_spool_listener,
    stop_spool_listener,
)

logger = logging.getLogger(__name__)


def launch_blindwindow(
    title: str = "BlindWindow Output",
    always_on_top: bool = False,
    autoscroll: bool = True,
) -> None:
    """Launch the BlindWindow Tkinter interface."""
    import pyhabitat

    if not pyhabitat.tkinter_is_available():
        logger.error(
            "Cannot launch BlindWindow: Tkinter is not available "
            "in this Python environment."
        )
        sys.exit(1)

    import tkinter as tk

    from .blindwindow import BlindWindow

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

    def _receiver(text: str, tag: str = "stdout") -> None:
        root.after_idle(
            lambda: app.append(text, tag=tag)
        )

    # Receive output generated within this process.
    #register_listener(_receiver)

    # Receive output appended by other processes.
    start_spool_listener(_receiver)

    def _on_close() -> None:
        stop_spool_listener()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)

    logger.info("BlindWindow interface initialized successfully.")

    try:
        root.mainloop()
    except KeyboardInterrupt:
        logger.info("BlindWindow closed via KeyboardInterrupt.")
    finally:
        stop_spool_listener()


if __name__ == "__main__":
    launch_blindwindow()
