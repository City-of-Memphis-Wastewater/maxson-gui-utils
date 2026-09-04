# src/blindwidow/transport.py
from __future__ import annotations
from pathlib import Path
from enum import Enum

SPOOL_PATH = Path.home() / ".blindwindow" / "spool" # append only event stream

class IPCTransport(str, Enum):
    UDS = "uds"
    UDP = "udp"
    NAMED_PIPE = "named-pipe"
    SPOOL_FILE = "spool-file"
