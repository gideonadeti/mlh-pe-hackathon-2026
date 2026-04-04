"""Parse users.csv rows for bulk import (API + seed script)."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import TYPE_CHECKING, Any, BinaryIO, TextIO

if TYPE_CHECKING:
    from app.models.user import User

USER_CSV_DT_FORMAT = "%Y-%m-%d %H:%M:%S"
USER_CSV_COLUMNS = ("id", "username", "email", "created_at")


def _parse_created_at(value: str) -> datetime:
    return datetime.strptime(value.strip(), USER_CSV_DT_FORMAT)


def parse_users_csv_text_stream(stream: TextIO) -> list[dict[str, Any]]:
    """Read a users CSV (header: id, username, email, created_at). Returns dicts for User.insert_many."""
    reader = csv.DictReader(stream)
    if not reader.fieldnames:
        raise ValueError("CSV has no header row")

    headers = {h.strip() for h in reader.fieldnames if h is not None and h.strip()}
    missing = set(USER_CSV_COLUMNS) - headers
    if missing:
        raise ValueError(f"Missing columns: {', '.join(sorted(missing))}")

    rows_out: list[dict[str, Any]] = []
    for line_no, row in enumerate(reader, start=2):
        if not row or all((v is None or str(v).strip() == "") for v in row.values()):
            continue
        try:
            rows_out.append(
                {
                    "id": int(str(row["id"]).strip()),
                    "username": str(row["username"]).strip(),
                    "email": str(row["email"]).strip(),
                    "created_at": _parse_created_at(str(row["created_at"])),
                }
            )
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError(f"Invalid row at line {line_no}") from exc

    return rows_out


def parse_users_csv_bytes(data: bytes) -> list[dict[str, Any]]:
    text = data.decode("utf-8-sig")
    return parse_users_csv_text_stream(io.StringIO(text))


def parse_users_csv_binary_stream(stream: BinaryIO) -> list[dict[str, Any]]:
    return parse_users_csv_bytes(stream.read())


def user_to_api_dict(user: User) -> dict[str, Any]:
    """Shape for JSON responses (Note.md list/get user)."""
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "created_at": user.created_at.isoformat(sep="T", timespec="seconds"),
    }
