# src/blindwidow/transport.py
from __future__ import annotations

BUFFER_PATH = Path.home() / ".blindwindow" / "buffer"

class IPCTransport(str, Enum):
    UDS = "uds"
    UDP = "udp"
    NAMED_PIPE = "named-pipe"
    BUFFER_FILE = "buffer-file"
