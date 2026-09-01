#!/usr/bin/env python3
# src/maxson_gui_utils/__init__.py
from __future__ import annotations

#from ._version import __version__

# 1. Clean public-facing mapping
__all__ = [
    #"__version__",
    "Console",
    "TeeStream",
    "GuiStream",
]




# 2. Fully dynamic attribute routing
def __getattr__(name: str):

    if name == "Console":
        from .console import Console
        return Console

    if name == "GuiStream":
        from .streams import GuiStream
        return GuiStream

    if name == "TeeStream":
        from .streams import TeeStream
        return TeeStream


    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# 3. Dynamic introspection reflecting runtime changes
def __dir__():
    exported = list(__all__)

    return sorted(
        exported
        + [
            "__builtins__",
            "__cached__",
            "__doc__",
            "__file__",
            "__getattr__",
            "__dir__",
            "__loader__",
            "__name__",
            "__package__",
            "__path__",
            "__spec__",
        ]
    )
