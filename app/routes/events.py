from __future__ import annotations

import json
import logging

from flask import Blueprint, jsonify, request

from app.models import Event

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
