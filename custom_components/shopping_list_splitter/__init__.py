from __future__ import annotations

import logging
import json
import glob
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers.typing import ConfigType
import traceback

DOMAIN = "shopping_list_splitter"
_LOGGER = logging.getLogger(__name__)


def setup(hass: HomeAssistant, config: ConfigType) -> bool:
    @callback
    async def export_shopping_list(call: ServiceCall) -> None:
        json_file_path = "/config/.shopping_list.json"
        separate_file_pattern = "/config/.shopping_list_*.json"
        all_file_path = "/config/.shopping_list_all.json"

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

        with open(all_file_path, "w") as file:
            json.dump(json_data, file, indent=2)

        _LOGGER.info("Items separated into separate files, and all items saved to .shopping_list_all.json.")

    @callback
    async def import_shopping_list(call: ServiceCall) -> None:
        list_name = call.data.get("list_name", "all")
        file_path = f"/config/.shopping_list_{list_name}.json"

        try:
            await sync_shopping_lists(hass)

            if glob.glob(file_path):
                with open(file_path, "r") as file:
                    items = json.load(file)
                    await hass.services.async_call("shopping_list", "complete_all")
                    await hass.services.async_call("shopping_list", "clear_completed_items")

                    for item in items:
                        if not item.get("complete"):
                            item_name = item.get("name")
                            if item_name:
                                service_data = {"name": item_name}
                                await hass.services.async_call("shopping_list", "add_item", service_data)
                                _LOGGER.info(f"Added item to shopping list: {item_name}")
            else:
                _LOGGER.info(f"No items found for {list_name}.")
        except Exception:
            _LOGGER.error(f"Error updating shopping list from file: {file_path}")
            _LOGGER.error(traceback.format_exc())


    @callback
    async def sync_shopping_lists(hass: HomeAssistant) -> None:
        main_list_path = "/config/.shopping_list.json"
        separate_file_pattern = "/config/.shopping_list_*.json"
        all_file_path = "/config/.shopping_list_all.json"

        try:
            with open(main_list_path, "r") as main_list_file:
                main_list_items = json.load(main_list_file)

                completed_item_names = set()
                for item in main_list_items:
                    if item.get("complete"):
                        completed_item_names.add(item.get("name"))

        
            separate_files = glob.glob(separate_file_pattern)
            separate_files.append(all_file_path)

            for separate_file in separate_files:
                with open(separate_file, "r") as file:
                    separate_items = json.load(file)

            
                updated_separate_items = []
                for item in separate_items:
                    item_name = item.get("name")
                    if item_name not in completed_item_names:
                        updated_separate_items.append(item)

            
                with open(separate_file, "w") as file:
                    json.dump(updated_separate_items, file, indent=2)
            
            await hass.services.async_call("shopping_list", "sort")

            _LOGGER.info("Complete state updated across all files.")
        except Exception:
            _LOGGER.error("Error updating complete state across files.")
            _LOGGER.error(traceback.format_exc())


    hass.services.async_register(DOMAIN, 'export', export_shopping_list)
    hass.services.async_register(DOMAIN, 'import', import_shopping_list)


    return True
