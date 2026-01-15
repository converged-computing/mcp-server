import os
from datetime import datetime
from typing import Any, Dict

import mcpserver.utils as utils

from .base import Database


class JsonDatabase(Database):
    """
    Saves results as individual JSON files in a directory.
    URI Format: json:///path/to/results_dir
    """

    def __init__(self, path: str):
        self.set_base_dir(path)

    def set_base_dir(self, path: str):
        """
        Handle file:// or json:// prefixes or raw path
        """
        if path.startswith("json://"):
            self.base_dir = path.replace("json://", "")
        elif path.startswith("file://"):
            self.base_dir = path.replace("file://", "")
        else:
            self.base_dir = path
        self.base_dir = os.path.expanduser(os.path.expandvars(self.base_dir))

    def save(self, data: Dict[str, Any]):
        """
        Save a result (data) to filesystem.
        """
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"results-{timestamp}.json"
        filepath = os.path.join(self.base_dir, filename)
        utils.write_json(filepath, data)
