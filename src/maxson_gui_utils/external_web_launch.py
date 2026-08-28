# src/maxson_gui_utils/external_web_launch.py
from __future__ import annotations
import webbrowser
import logging
from pathlib import Path
from dworshak_config import DworshakConfig
from rich.console import Console
import pyhabitat

from .context import SERVICE, CONFIG_PATH

logger = logging.getLogger(__name__)
console_stderr = Console(stderr=True)

ITEM_WEB_REF_0 = "web-address-0"


"""
Redesign goals: 
- Associate with app, not with MGU config file.
- This isn't a GUI feature, it probably belong in pyhabitat or even memphisdrip, or elsewhere.

"""

def launch_configured_website(path:Path|str|None=None,service:str|None=None,item:str|None=None)->str:
    if service is None:
        service = SERVICE
    if item is None:
        item = ITEM_WEB_REF_0
    if path is None:
        path = CONFIG_PATH

    config_mngr = DworshakConfig(path = path)
    url = config_mngr.get(service=SERVICE,item=item) # allows retrieval of edited value

    # If the user left it blank, or it's purely whitespace, use the default path
    if not url or not str(url).strip():
        config_mngr.set(service=service,item=item,value="",overwrite=False) # allows retrieval of edited value
        console_stderr.print("")
        console_stderr.print("Configured URL is None. Configuration file mutated, keys created in config file: {path}")
        console_stderr.print(f'config_mngr.set(service="{service}",item="{item}",value="",overwrite=False)')
        console_stderr.print("")
        console_stderr.print("To set the value, run dworshak-config CLI like this:")
        console_stderr.print(f'dworshak-config set --service "{service}" --item "{item}" --value https://example.com  --path "{path}"')
        console_stderr.print("")
        return None

    pyhabitat.launch_browser_now(url)
    return url
