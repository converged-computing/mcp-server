from .base import Database
from .filesystem import JsonDatabase
from .sqlite import SqliteDatabase


def get_database(uri: str) -> Database | None:
    """
    Factory to create a database backend from a URI string.
    Returns None if uri is None/Empty.
    """
    if not uri:
        return None

    if uri.startswith("sqlite://"):
        return SqliteDatabase(uri)

    if uri.startswith("json://") or uri.startswith("file://") or "/" in uri or uri == ".":
        # Default to JSON if it looks like a path but no schema provided
        return JsonDatabase(uri)

    raise ValueError(f"Unknown database scheme in: {uri}")
