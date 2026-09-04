class IPCTransport(str, Enum):
    UDS = "uds"
    UDP = "udp"
    NAMED_PIPE = "named-pipe"
    BUFFER_FILE = "buffer-file"
