import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


@dataclass
class Metric:
    """
    This is a basic metric type that holds a key value pair.
    """

    name: str
    key: str
    value: Any = None

    def to_dict(self):
        data = asdict(self)
        data["type"] = self.__class__.__name__
        return data


@dataclass
class DurationMetric(Metric):
    """
    Time Spans (e.g., Tool Execution)
    """

    start_time: float = 0.0
    end_time: float = 0.0
    duration: float = 0.0
    success: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class MetricsRegistry:
    """
    A MetricsRegistry holds metrics about function execution we can reference later.
    """

    def __init__(self):
        self._history: List[Metric] = []

    def record(self, metric: Metric):
        """
        Generic record method.
        """
        self._history.append(metric)

    def record_value(self, name: str, value: Any, unit: str = ""):
        """
        Helper for simple values
        """
        self.record(Metric(name=name, value=value, unit=unit))

    def get_all(self) -> List[dict]:
        """
        Get all metrics recorded to our registry!

        metrics.get_all()
        """
        return [m.to_dict() for m in self._history]

    def filter_by_type(self, type_name: str) -> List[dict]:
        return [m.to_dict() for m in self._history if m.__class__.__name__ == type_name]


metrics = MetricsRegistry()
