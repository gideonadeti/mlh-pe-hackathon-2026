"""Create Peewee tables (idempotent). Run from project root: uv run python scripts/create_tables.py"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app import create_app


def main() -> None:
    create_app()


if __name__ == "__main__":
    main()
    print("Tables ready: users, urls, events")
