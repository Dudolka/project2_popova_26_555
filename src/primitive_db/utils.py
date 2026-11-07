"""JSON persistence helpers."""

import json
from pathlib import Path

from primitive_db.constants import DATA_DIR


def load_metadata(filepath):
    """Return metadata or an empty mapping when the file is absent."""
    try:
        with open(filepath, encoding="utf-8") as stream:
            return json.load(stream)
    except FileNotFoundError:
        return {}


def save_metadata(filepath, data):
    """Persist metadata as human-readable JSON."""
    with open(filepath, "w", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)


def table_path(table_name):
    """Build a safe JSON path for a validated table name."""
    if not table_name.isidentifier() or table_name.startswith("_"):
        raise ValueError(f"Некорректное значение: {table_name}. Попробуйте снова.")
    return Path(DATA_DIR) / f"{table_name}.json"


def load_table_data(table_name):
    """Load rows of a table, defaulting to an empty list."""
    try:
        with table_path(table_name).open(encoding="utf-8") as stream:
            return json.load(stream)
    except FileNotFoundError:
        return []


def save_table_data(table_name, data):
    """Save rows in a separate JSON file for each table."""
    path = table_path(table_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
