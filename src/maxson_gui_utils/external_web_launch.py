# src/maxson_gui_utils/external_web_launch.py
from __future__ import annotations
import webbrowser
import logging
from pathlib import Path
from dworshak_config import DworshakConfig
from rich.console import Console

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
        config_mngr.set(service=SERVICE,item=item,value="",overwrite=False) # allows retrieval of edited value
        console_stderr.print("Configured URL is None. Configuration file mutated, keys of opportunity generated with:")
        console_stderr.print(f'config_mngr.set(service="{SERVICE}",item="{item}",value="",overwrite=False)')
        console_stderr.print("")
        console_stderr.print("To set the value, run dworshak-config CLI like this.")
        console_stderr.print(f'dworshak-config set --service "{SERVICE}" --item "{item}" --value <WEBSITE>  --path "{path}"')
        console_stderr.print("")
        return None

    launch_web_url(url)
    return url

def launch_web_url(url: str) -> bool:
    """
    Opens the specified URL in the user's default browser using the standard library.

    Returns:
        bool: True if the browser was successfully launched, False otherwise.
    """
    try:
        # new=2 opens the URL in a new tab if possible
        success = webbrowser.open(url, new=2)
        if not success:
            logger.error(f"Failed to open URL via webbrowser module: {url}")
        return success
    except Exception as e:
        logger.error(f"An error occurred while trying to launch the URL: {e}")
        return False
