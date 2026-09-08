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

_FRAME_HEADER = struct.Struct("!I")
_WRITE_LOCK = threading.Lock()


def write_record(text: str, tag: str = "stdout") -> None:
    if not text:
        return

    payload = json.dumps(
        {"text": text, "tag": tag},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    if len(payload) > 0xFFFFFFFF:
        raise ValueError("Spool record is too large.")

    frame = _FRAME_HEADER.pack(len(payload)) + payload

    SPOOL_DIR.mkdir(parents=True, exist_ok=True)

    with _WRITE_LOCK:
        with SPOOL_PATH.open("ab") as spool:
            spool.write(frame)
            spool.flush()


def decode_records(data: bytes) -> list[dict[str, Any]]:
    records, consumed = decode_records_partial(data)

    if consumed != len(data):
        raise ValueError("Incomplete spool frame.")

    return records


def decode_records_partial(
    data: bytes,
) -> tuple[list[dict[str, Any]], int]:
    records: list[dict[str, Any]] = []
    offset = 0

    while len(data) - offset >= _FRAME_HEADER.size:
        (length,) = _FRAME_HEADER.unpack_from(data, offset)
        frame_start = offset
        offset += _FRAME_HEADER.size

        if len(data) - offset < length:
            return records, frame_start

        payload = data[offset : offset + length]
        offset += length

        record = json.loads(payload.decode("utf-8"))

        if not isinstance(record, dict):
            raise ValueError("Spool record must be a JSON object.")

        if "text" not in record:
            raise ValueError("Spool record is missing 'text'.")

        records.append(record)

    return records, offset
