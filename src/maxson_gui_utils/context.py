# src/maxson_gui_utils/context.py
from __future__ import annotations

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
SRC_DIR = PACKAGE_DIR.parent
PROJECT_ROOT = SRC_DIR.parent

APP_NAME = "maxson-gui-utils"
APP_NAME_PRETTY = "Maxson Gui Utils"
IMPORT_NAME = "maxson_gui_utils"
SRC_FOLDER_NAME = "maxson_gui_utils"
DESCRIPTION_STR = "A Python application."
APP_DIR = Path.home() / ".maxson-gui-utils"
LOG_FILE_PATH = APP_DIR / "maxson-gui-utils.log"
SERVICE = APP_NAME
CONFIG_PATH = APP_DIR / "config.json"
SECRET_PATH = APP_DIR / "vault.db"
ENV_PATH = PROJECT_ROOT / ".env"
