# src/blindwidow/transport.py
from __future__ import annotations

class IPCTransport(str, Enum):
    UDS = "uds"
    UDP = "udp"
    NAMED_PIPE = "named-pipe"
    BUFFER_FILE = "buffer-file"
