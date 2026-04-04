"""Load data/*.csv seed files into Postgres. Run: uv run python scripts/load_seed_csv.py"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

from peewee import chunked

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app import create_app
from app.database import db
from app.models import Event, Url, User
from app.services.user_csv import parse_users_csv_text_stream

_DATA_DIR = _ROOT / "data"
_DT_FORMAT = "%Y-%m-%d %H:%M:%S"
_BATCH = 200


def _parse_dt(value: str) -> datetime:
    return datetime.strptime(value, _DT_FORMAT)


def _read_users(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return parse_users_csv_text_stream(f)


def _read_urls(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(
                {
                    "id": int(row["id"]),
                    "user_id": int(row["user_id"]),
                    "short_code": row["short_code"],
                    "original_url": row["original_url"],
                    "title": row["title"],
                    "is_active": row["is_active"] == "True",
                    "created_at": _parse_dt(row["created_at"]),
                    "updated_at": _parse_dt(row["updated_at"]),
                }
            )
    return rows


def _read_events(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(
                {
                    "id": int(row["id"]),
                    "url_id": int(row["url_id"]),
                    "user_id": int(row["user_id"]),
                    "event_type": row["event_type"],
                    "timestamp": _parse_dt(row["timestamp"]),
                    "details": row["details"],
                }
            )
    return rows


def _reset_schema() -> None:
    """Drop and recreate tables so schema matches models (e.g. after model changes)."""
    db.drop_tables([User, Url, Event], safe=True, cascade=True)
    db.create_tables([User, Url, Event], safe=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Load seed CSVs into the database.")
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Do not delete existing rows first (fails if primary keys collide).",
    )
    args = parser.parse_args()

    users_path = _DATA_DIR / "users.csv"
    urls_path = _DATA_DIR / "urls.csv"
    events_path = _DATA_DIR / "events.csv"
    for p in (users_path, urls_path, events_path):
        if not p.is_file():
            raise SystemExit(f"Missing CSV: {p}")

    app = create_app()
    with app.app_context():
        db.connect(reuse_if_open=True)
        try:
            if not args.no_clear:
                _reset_schema()
            else:
                db.create_tables([User, Url, Event], safe=True)

            users = _read_users(users_path)
            urls = _read_urls(urls_path)
            events = _read_events(events_path)

            with db.atomic():
                for batch in chunked(users, _BATCH):
                    User.insert_many(batch).execute()
                for batch in chunked(urls, _BATCH):
                    Url.insert_many(batch).execute()
                for batch in chunked(events, _BATCH):
                    Event.insert_many(batch).execute()
        finally:
            if not db.is_closed():
                db.close()

    print(
        f"Loaded {len(users)} users, {len(urls)} urls, {len(events)} events "
        f"({'append' if args.no_clear else 'replace'} mode)."
    )


if __name__ == "__main__":
    main()
