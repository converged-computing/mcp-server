from abc import ABC, abstractmethod
from typing import Any, Dict


class Database(ABC):
    """
    Abstract Base Class for Fractale Result Storage.
    """

    @abstractmethod
    def save(self, data: Dict[str, Any]):
        """
        Save the workflow execution results.
        """
        pass

    def connect(self):
        """Optional setup hook."""
        pass

    def close(self):
        """Optional teardown hook."""
        pass
