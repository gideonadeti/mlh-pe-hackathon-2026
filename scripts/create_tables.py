"""Create Peewee tables (idempotent). Run from project root: uv run python scripts/create_tables.py"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app import create_app
from app.database import db
from app.models import Event, Url, User


def main() -> None:
    app = create_app()
    with app.app_context():
        db.connect(reuse_if_open=True)
        try:
            db.create_tables([User, Url, Event], safe=True)
        finally:
            if not db.is_closed():
                db.close()


if __name__ == "__main__":
    main()
    print("Tables ready: users, urls, events")
