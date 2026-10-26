"""One database path for both entry points, independent of the working directory."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def database_path():
    path = Path(os.environ.get("CITIZEN_DB", ROOT / "storage" / "citizens.sqlite3"))
    return path if path.is_absolute() else ROOT / path
