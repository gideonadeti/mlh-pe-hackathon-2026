from __future__ import annotations

import json
import logging
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request
from peewee import IntegrityError, fn

from app.database import db
from app.models import Event, Url, User

events_bp = Blueprint("events", __name__)
_log = logging.getLogger(__name__)

_MAX_PER_PAGE = 100
_DEFAULT_PER_PAGE = 20


def _parse_page_int(raw: str | None, name: str, default: int) -> int:
    if raw is None or raw == "":
        return default
    try:
        n = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if n < 1:
        raise ValueError(f"{name} must be a positive integer")
    return n


def event_to_api_dict(event: Event) -> dict:
    raw = event.details
    details: object
    if not raw or not raw.strip():
        details = {}
    else:
        try:
            details = json.loads(raw)
        except json.JSONDecodeError:
            _log.warning("event id=%s has non-JSON details", event.id)
            details = {}

    return {
        "id": event.id,
        "url_id": event.url_id,
        "user_id": event.user_id,
        "event_type": event.event_type,
        "timestamp": event.timestamp.isoformat(sep="T", timespec="seconds"),
        "details": details,
    }


@events_bp.route("/events", methods=["GET"])
def list_events():
    query = Event.select().order_by(Event.id)
    args = request.args
    if "page" in args or "per_page" in args:
        try:
            page = _parse_page_int(args.get("page"), "page", 1)
            per_page = _parse_page_int(
                args.get("per_page"), "per_page", _DEFAULT_PER_PAGE
            )
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        per_page = min(per_page, _MAX_PER_PAGE)
        total = int(query.count())
        total_pages = (total + per_page - 1) // per_page if total else 0
        offset = (page - 1) * per_page
        rows = query.offset(offset).limit(per_page)
        payload = [event_to_api_dict(e) for e in rows]
        has_next = total_pages > 0 and page < total_pages
        has_prev = page > 1
        return jsonify(
            events=payload,
            page=page,
            per_page=per_page,
            total=total,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev,
        )

    return jsonify([event_to_api_dict(e) for e in query])


def _parse_body_positive_int(raw: object, field: str) -> tuple[int | None, str | None]:
    """Return (value, error_message)."""
    if raw is None:
        return None, f"{field} is required"
    if isinstance(raw, bool):
        return None, f"{field} must be an integer"
    if isinstance(raw, int):
        if raw < 1:
            return None, f"{field} must be a positive integer"
        return raw, None
    if isinstance(raw, float) and raw.is_integer():
        n = int(raw)
        if n < 1:
            return None, f"{field} must be a positive integer"
        return n, None
    if isinstance(raw, str) and raw.strip().isdigit():
        n = int(raw.strip())
        if n < 1:
            return None, f"{field} must be a positive integer"
        return n, None
    return None, f"{field} must be an integer"


@events_bp.route("/events", methods=["POST"])
def create_event():
    body = request.get_json(silent=True)
    if body is None or not isinstance(body, dict):
        return jsonify(error="JSON object required"), 400

    raw_type = body.get("event_type")
    if raw_type is None:
        return jsonify(error="validation failed", fields={"event_type": ["required"]}), 400
    if not isinstance(raw_type, str) or not raw_type.strip():
        return (
            jsonify(
                error="validation failed",
                fields={"event_type": ["must be a non-empty string"]},
            ),
            400,
        )

    url_id, url_err = _parse_body_positive_int(body.get("url_id"), "url_id")
    if url_err:
        return jsonify(error="validation failed", fields={"url_id": [url_err]}), 400

    user_id, user_err = _parse_body_positive_int(body.get("user_id"), "user_id")
    if user_err:
        return jsonify(error="validation failed", fields={"user_id": [user_err]}), 400

    if "details" not in body:
        details_obj: dict = {}
    else:
        details_raw = body["details"]
        if details_raw is None:
            details_obj = {}
        elif not isinstance(details_raw, dict):
            return (
                jsonify(
                    error="validation failed",
                    fields={"details": ["must be an object"]},
                ),
                400,
            )
        else:
            details_obj = details_raw

    if Url.get_or_none(Url.id == url_id) is None:
        return jsonify(error="url not found"), 404
    if User.get_or_none(User.id == user_id) is None:
        return jsonify(error="user not found"), 404

    try:
        details_json = json.dumps(details_obj)
    except (TypeError, ValueError):
        return (
            jsonify(
                error="validation failed",
                fields={"details": ["must be JSON-serializable"]},
            ),
            400,
        )

    now = datetime.now()
    try:
        with db.atomic():
            max_id = Event.select(fn.MAX(Event.id)).scalar()
            next_id = (max_id or 0) + 1
            event = Event.create(
                id=next_id,
                url_id=url_id,
                user_id=user_id,
                event_type=raw_type.strip(),
                timestamp=now,
                details=details_json,
            )
    except IntegrityError as exc:
        current_app.logger.warning("create event integrity error: %s", exc)
        return jsonify(error="could not create event"), 409

    return jsonify(event_to_api_dict(event)), 201
