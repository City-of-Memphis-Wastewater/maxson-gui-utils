#!/usr/bin/env python3
# src/maxson_gui_utils/registration.py
from __future__ import annotations
from typing import Callable, List, Optional

# Active listeners receiving stream chunks: callback(text: str, tag: str)
_LISTENERS: List[Callable[[str, str], None]] = []

def register_listener(callback: Callable[[str, str], None]) -> None:
    """Registers a pane callback (e.g. TextPane.append) to receive console outputs."""
    if callback not in _LISTENERS:
        _LISTENERS.append(callback)

def unregister_listener(callback: Callable[[str, str], None]) -> None:
    """Removes a pane callback from global listeners."""
    if callback in _LISTENERS:
        _LISTENERS.remove(callback)

def dispatch_write(text: str, tag: str = "stdout") -> None:
    """Dispatches streamed text to all registered pane listeners."""
    for listener in _LISTENERS:
        listener(text, tag)
