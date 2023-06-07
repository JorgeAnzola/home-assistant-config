"""Example of a custom component exposing a service."""
from __future__ import annotations

import logging
import json
import glob
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers.typing import ConfigType
import traceback


# The domain of your component. Should be equal to the name of your component.
DOMAIN = "shopping_list_splitter"
_LOGGER = logging.getLogger(__name__)


def setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the an async service example component."""
    @callback
    def split_shopping_list(call: ServiceCall) -> None:
        """Split the shopping list into separate files."""
        json_file_path = "/config/.shopping_list.json"  # Replace with the actual path to your main JSON file
        separate_file_pattern = "/config/.shopping_list_*.json"  # Pattern to match separate file paths

        # Create or update separate files with an empty array
        existing_separate_files = glob.glob(separate_file_pattern)
        json_data = []

        try:
            with open(json_file_path, "r") as file:
                json_data = json.load(file)
        except FileNotFoundError:
            _LOGGER.error("JSON file not found at: %s", json_file_path)
            return

        for file_path in existing_separate_files:
            with open(file_path, "w") as file:
                json.dump([], file, indent=2)

        # Separate items into separate files
        list_files = {}

        for item in json_data:
            list_name = item.get("name").split(" - ")[0]
            if list_name not in list_files:
                list_file_path = f"/config/.shopping_list_{list_name.lower()}.json"
                list_files[list_name] = list_file_path

        for list_name, list_file_path in list_files.items():
            list_items = [item for item in json_data if item["name"].startswith(list_name)]
            with open(list_file_path, "w") as file:
                json.dump(list_items, file, indent=2)

        _LOGGER.info("Items separated into separate files.")

    @callback
    async def update_shopping_list(call: ServiceCall) -> None:
        """Update the shopping list from a separate file."""
        list_name = call.data.get("list_name")
        file_path = f"/config/.shopping_list_{list_name}.json"

        try:
            if glob.glob(file_path):
                with open(file_path, "r") as file:
                    items = json.load(file)
                    await hass.services.async_call("shopping_list", "complete_all")
                    await hass.services.async_call("shopping_list", "clear_completed_items")
                    for item in items:
                        name = item.get("name")
                        if name:
                            service_data = {"name": name}
                            await hass.services.async_call("shopping_list", "add_item", service_data)
                            _LOGGER.info(f"Added item to shopping list: {name}")
            else:
                _LOGGER.info(f"No items found for {list_name}.")
        except Exception:
            _LOGGER.error(f"Error updating shopping list from file: {file_path}")
            _LOGGER.error(traceback.format_exc())


    # Register our service with Home Assistant.
    hass.services.async_register(DOMAIN, 'split', split_shopping_list)
    hass.services.async_register(DOMAIN, 'update', update_shopping_list)

    # Return boolean to indicate that initialization was successful.
    return True
