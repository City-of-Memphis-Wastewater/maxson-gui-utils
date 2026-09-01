#!/usr/bin/env python3
# src/maxson_gui_utils/ansi.py

import re

# Matches standard ANSI escape sequences (CSI sequences like \x1b[...m)
ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")
#ANSI_PATTERN = re.compile(r"\x1b\\[[0-9;]*m")

def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences."""
    return ANSI_PATTERN.sub("", text)

def parse_ansi(text: str):
    """
    Parse ANSI sequences into (text, style) tuples.
    For now, just strip and return plain text.
    """
    return [(strip_ansi(text), None)]
