# src/maxson_gui_utils/resources.py
from __future__ import annotations

from pathlib import Path
from importlib.resources import files
from .context import IMPORT_NAME

def resource_path(*parts: str):
    return files(IMPORT_NAME).joinpath("data", *parts)


def read_resource(*parts: str) -> str:
    return resource_path(*parts).read_text()


def read_resource_bytes(*parts: str) -> bytes:
    return resource_path(*parts).read_bytes()
