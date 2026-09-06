# src/maxson_gui_utils/blindwindow/spool.py
from __future__ import annotations

import json
import logging
import struct
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SPOOL_DIR = Path.home() / ".blindwindow"
SPOOL_PATH = SPOOL_DIR / "spool"

# 4-byte unsigned big-endian length prefix.
_FRAME_HEADER = struct.Struct("!I")

# Protects concurrent writes from threads in the same process.
_WRITE_LOCK = threading.Lock()


def encode_record(text: str, tag: str = "stdout") -> bytes:
    """Serialize one output event into a length-prefixed JSON frame."""

    record = {
        "text": text,
        "tag": tag,
    }

    payload = json.dumps(
        record,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    if len(payload) > 0xFFFFFFFF:
        raise ValueError("Spool record is too large.")

    return _FRAME_HEADER.pack(len(payload)) + payload


def write_record(text: str, tag: str = "stdout") -> None:
    """Append one output event to the BlindWindow spool."""

    if not text:
        return

    frame = encode_record(text, tag)

    SPOOL_DIR.mkdir(parents=True, exist_ok=True)

    with _WRITE_LOCK:
        with SPOOL_PATH.open("ab") as spool:
            spool.write(frame)
            spool.flush()


def decode_records(data: bytes) -> list[dict[str, Any]]:
    """Decode complete frames from bytes.

    Raises ValueError if a frame is incomplete or malformed.
    """

    records: list[dict[str, Any]] = []
    offset = 0

    while offset < len(data):
        remaining = len(data) - offset

        if remaining < _FRAME_HEADER.size:
            raise ValueError("Incomplete spool frame header.")

        (length,) = _FRAME_HEADER.unpack_from(data, offset)
        offset += _FRAME_HEADER.size

        if len(data) - offset < length:
            raise ValueError("Incomplete spool frame payload.")

        payload = data[offset : offset + length]
        offset += length

        record = json.loads(payload.decode("utf-8"))

        if not isinstance(record, dict):
            raise ValueError("Spool record must be a JSON object.")

        if "text" not in record:
            raise ValueError("Spool record is missing 'text'.")

        records.append(record)

    return records
