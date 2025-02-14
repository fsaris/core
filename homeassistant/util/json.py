"""JSON utility functions."""
from __future__ import annotations

from collections import deque
from collections.abc import Callable
import json
import logging
from typing import Any

from homeassistant.core import Event, State
from homeassistant.exceptions import HomeAssistantError

from .file import write_utf8_file

_LOGGER = logging.getLogger(__name__)


class SerializationError(HomeAssistantError):
    """Error serializing the data to JSON."""


class WriteError(HomeAssistantError):
    """Error writing the data."""


def load_json(filename: str, default: list | dict | None = None) -> list | dict:
    """Load JSON data from a file and return as dict or list.

    Defaults to returning empty dict if file is not found.
    """
    try:
        with open(filename, encoding="utf-8") as fdesc:
            return json.loads(fdesc.read())  # type: ignore
    except FileNotFoundError:
        # This is not a fatal error
        _LOGGER.debug("JSON file not found: %s", filename)
    except ValueError as error:
        _LOGGER.exception("Could not parse JSON content: %s", filename)
        raise HomeAssistantError(error) from error
    except OSError as error:
        _LOGGER.exception("JSON file reading failed: %s", filename)
        raise HomeAssistantError(error) from error
    return {} if default is None else default


def save_json(
    filename: str,
    data: list | dict,
    private: bool = False,
    *,
    encoder: type[json.JSONEncoder] | None = None,
) -> None:
    """Save JSON data to a file.

    Returns True on success.
    """
    try:
        json_data = json.dumps(data, indent=4, cls=encoder)
    except TypeError as error:
        msg = f"Failed to serialize to JSON: {filename}. Bad data at {format_unserializable_data(find_paths_unserializable_data(data))}"
        _LOGGER.error(msg)
        raise SerializationError(msg) from error

    write_utf8_file(filename, json_data, private)


def format_unserializable_data(data: dict[str, Any]) -> str:
    """Format output of find_paths in a friendly way.

    Format is comma separated: <path>=<value>(<type>)
    """
    return ", ".join(f"{path}={value}({type(value)}" for path, value in data.items())


def find_paths_unserializable_data(
    bad_data: Any, *, dump: Callable[[Any], str] = json.dumps
) -> dict[str, Any]:
    """Find the paths to unserializable data.

    This method is slow! Only use for error handling.
    """
    to_process = deque([(bad_data, "$")])
    invalid = {}

    while to_process:
        obj, obj_path = to_process.popleft()

        try:
            dump(obj)
            continue
        except (ValueError, TypeError):
            pass

        # We convert objects with as_dict to their dict values so we can find bad data inside it
        if hasattr(obj, "as_dict"):
            desc = obj.__class__.__name__
            if isinstance(obj, State):
                desc += f": {obj.entity_id}"
            elif isinstance(obj, Event):
                desc += f": {obj.event_type}"

            obj_path += f"({desc})"
            obj = obj.as_dict()

        if isinstance(obj, dict):
            for key, value in obj.items():
                try:
                    # Is key valid?
                    dump({key: None})
                except TypeError:
                    invalid[f"{obj_path}<key: {key}>"] = key
                else:
                    # Process value
                    to_process.append((value, f"{obj_path}.{key}"))
        elif isinstance(obj, list):
            for idx, value in enumerate(obj):
                to_process.append((value, f"{obj_path}[{idx}]"))
        else:
            invalid[obj_path] = obj

    return invalid
