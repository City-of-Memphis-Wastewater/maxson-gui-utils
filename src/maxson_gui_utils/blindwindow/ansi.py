#!/usr/bin/env python3
# src/maxson_gui_utils/ansi.py
from __future__ import annotations
import re

# Matches standard ANSI escape sequences (CSI sequences like \x1b[...m)
ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")
#ANSI_PATTERN = re.compile(r"\x1b\\[[0-9;]*m")

def strip_ansi_defunct(text: str) -> str:
    """Remove ANSI escape sequences."""
    return ANSI_PATTERN.sub("", text)

# Comprehensive regex matching ANSI escape sequences (CSI, OSC, SGR, etc.)
_ANSI_RE = re.compile(
    r"(?:\x1B[@-Z\\-_]|[\x80-\x9A\x9C-\x9F]|(?:\x1B\[|\x9B)[0-?]*[ -/]*[@-~])"
)

def strip_ansi(text: str) -> str:
    """Removes ANSI color and control codes from text strings."""
    if not text:
        return ""
    return _ANSI_RE.sub("", text)

def parse_ansi(text: str):
    """
    Parse ANSI sequences into (text, style) tuples.
    For now, just strip and return plain text.
    """
    return [(strip_ansi(text), None)]
