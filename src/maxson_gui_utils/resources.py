# src/maxson_gui_utils/resources.py
from __future__ import annotations

from pathlib import Path
from importlib.resources import files
from importlib.abc import Traversable

from contextlib import contextmanager
from importlib.resources import as_file

from .context import IMPORT_NAME


def resource_path(*parts: str) -> Traversable:
    return files(IMPORT_NAME).joinpath("data", *parts)


def read_resource(*parts: str, encoding: str = "utf-8") -> str:
    return resource_path(*parts).read_text(encoding=encoding)


def read_resource_bytes(*parts: str) -> bytes:
    return resource_path(*parts).read_bytes()

@contextmanager
def resource_file(*parts: str)->Path:
    resource = resource_path(*parts)
    with as_file(resource) as path:
        yield path
