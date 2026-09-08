# src/maxson_gui_utils/blindwindow/spool.py
from __future__ import annotations

import json
import logging
import os
import struct
import threading
from pathlib import Path
from typing import Any, Optional

import pyhabitat

logger = logging.getLogger(__name__)

# 10 MB default warning threshold
DEFAULT_MAX_SPOOL_BYTES = 10 * 1024 * 1024

_FRAME_HEADER = struct.Struct("!I")
_WRITE_LOCK = threading.Lock()
_CUSTOM_SPOOL_PATH: Optional[Path] = None


def resolve_default_spool_path() -> Path:
    """
    Resolve default spool path based on execution environment.
    Redirects to AppData LocalState under MSIX to ensure host visibility.
    """
    if pyhabitat.is_msix():
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "blindwindow" / "spool"

    return Path.home() / ".blindwindow" / "spool"


def get_spool_path() -> Path:
    """Get the currently active spool path."""
    if _CUSTOM_SPOOL_PATH is not None:
        return _CUSTOM_SPOOL_PATH
    return resolve_default_spool_path()


def set_spool_path(path: Path | str) -> Path:
    """Mutate and override the active spool path."""
    global _CUSTOM_SPOOL_PATH
    _CUSTOM_SPOOL_PATH = Path(path)
    logger.info("[Spool] Spool path explicit override set to: %s", _CUSTOM_SPOOL_PATH)
    return _CUSTOM_SPOOL_PATH


def clear_spool(spool_path: Optional[Path | str] = None) -> None:
    """Truncate or unlink the active spool file."""
    target_path = Path(spool_path) if spool_path else get_spool_path()
    with _WRITE_LOCK:
        if target_path.exists():
            try:
                target_path.unlink()
                logger.info("[Spool] Existing spool file cleared at %s", target_path)
            except OSError as err:
                logger.warning("[Spool] Failed to unlink spool at %s: %s", target_path, err)


def write_record(
    text: str,
    tag: str = "stdout",
    spool_path: Optional[Path | str] = None,
) -> None:
    """
    Encode and append a framed record to the spool file.
    Pre-assembles the binary payload into a single atomic write.
    """
    if not text:
        logger.debug("[Spool] Empty text received; skipping record write.")
        return

    target_path = Path(spool_path) if spool_path else get_spool_path()

    logger.debug("[Spool] Preparing record write | tag=%s | text_len=%d | path=%s", tag, len(text), target_path)

    payload = json.dumps(
        {"text": text, "tag": tag},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    if len(payload) > 0xFFFFFFFF:
        raise ValueError("Spool record is too large.")

    frame = _FRAME_HEADER.pack(len(payload)) + payload

    target_path.parent.mkdir(parents=True, exist_ok=True)

    with _WRITE_LOCK:
        with target_path.open("ab") as spool:
            spool.write(frame)
            spool.flush()

    logger.debug("[Spool] Wrote frame (%d bytes) to spool file at %s", len(frame), target_path)


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
            logger.debug("[Spool] Partial payload buffered: need %d bytes, have %d bytes.", length, len(data) - offset)
            return records, frame_start

        payload = data[offset : offset + length]
        offset += length

        try:
            record = json.loads(payload.decode("utf-8"))
        except Exception as err:
            logger.error("[Spool] Failed to decode JSON payload: %s", err)
            raise

        if not isinstance(record, dict):
            raise ValueError("Spool record must be a JSON object.")

        if "text" not in record:
            raise ValueError("Spool record is missing 'text'.")

        records.append(record)

    return records, offset