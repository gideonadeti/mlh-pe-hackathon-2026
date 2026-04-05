from __future__ import annotations

import secrets
import string
from datetime import datetime
from urllib.parse import urlparse

from flask import Blueprint, current_app, jsonify, request
from peewee import IntegrityError, fn

from app.database import db
from app.models import Url, User
from app.redirect_cache import invalidate_redirect

urls_bp = Blueprint("urls", __name__)

_MAX_PER_PAGE = 100
_DEFAULT_PER_PAGE = 20

_SHORT_CODE_LEN = 6
_SHORT_CODE_ALPHABET = string.ascii_letters + string.digits
_MAX_SHORT_CODE_ATTEMPTS = 24


def url_to_api_dict(url: Url) -> dict:
    return {
        "id": url.id,
        "user_id": url.user_id,
        "short_code": url.short_code,
        "original_url": url.original_url,
        "title": url.title,
        "is_active": url.is_active,
        "created_at": url.created_at.isoformat(sep="T", timespec="seconds"),
        "updated_at": url.updated_at.isoformat(sep="T", timespec="seconds"),
    }


def _generate_short_code() -> str:
    return "".join(secrets.choice(_SHORT_CODE_ALPHABET) for _ in range(_SHORT_CODE_LEN))


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


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


def _parse_query_user_id() -> tuple[int | None, tuple | None]:
    """Return (user_id, error_response) where error_response is (json, status) if invalid."""
    raw = request.args.get("user_id")
    if raw is None:
        return None, None
    if raw == "":
        return None, (jsonify(error="user_id must be an integer"), 400)
    try:
        uid = int(raw)
    except ValueError:
        return None, (jsonify(error="user_id must be an integer"), 400)
    if uid < 1:
        return None, (jsonify(error="user_id must be a positive integer"), 400)
    return uid, None


@urls_bp.route("/urls", methods=["GET"])
def list_urls():
    filter_user_id, err = _parse_query_user_id()
    if err is not None:
        body, status = err
        return body, status

    query = Url.select().order_by(Url.id)
    if filter_user_id is not None:
        query = query.where(Url.user_id == filter_user_id)

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
        payload = [url_to_api_dict(u) for u in rows]
        has_next = total_pages > 0 and page < total_pages
        has_prev = page > 1
        return jsonify(
            urls=payload,
            page=page,
            per_page=per_page,
            total=total,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev,
        )

    return jsonify([url_to_api_dict(u) for u in query])


@urls_bp.route("/urls/<int:url_id>", methods=["GET", "PUT"])
def url_detail(url_id: int):
    if request.method == "GET":
        try:
            url = Url.get_by_id(url_id)
        except Url.DoesNotExist:
            return jsonify(error="url not found"), 404
        return jsonify(url_to_api_dict(url))

    body = request.get_json(silent=True)
    if body is None or not isinstance(body, dict):
        return jsonify(error="JSON object required"), 400

    if "title" not in body and "is_active" not in body:
        return jsonify(error="provide at least one of: title, is_active"), 400

    errors: dict[str, list[str]] = {}
    if "title" in body:
        v = body["title"]
        if not isinstance(v, str):
            errors["title"] = ["must be a string"]
        elif not v.strip():
            errors["title"] = ["must not be empty"]
    if "is_active" in body:
        v = body["is_active"]
        if not isinstance(v, bool):
            errors["is_active"] = ["must be a boolean"]

    if errors:
        return jsonify(error="validation failed", fields=errors), 400

    try:
        url = Url.get_by_id(url_id)
    except Url.DoesNotExist:
        return jsonify(error="url not found"), 404

    if "title" in body:
        url.title = body["title"].strip()
    if "is_active" in body:
        url.is_active = body["is_active"]

    url.updated_at = datetime.now()
    url.save()
    invalidate_redirect(url.short_code)

    return jsonify(url_to_api_dict(url)), 200


@urls_bp.route("/urls", methods=["POST"])
def create_url():
    body = request.get_json(silent=True)
    if body is None or not isinstance(body, dict):
        return jsonify(error="JSON object required"), 400

    errors: dict[str, list[str]] = {}
    raw_user_id = body.get("user_id")
    raw_original = body.get("original_url")
    raw_title = body.get("title")
    user_id: int | None = None

    if raw_user_id is None:
        errors["user_id"] = ["required"]
    elif isinstance(raw_user_id, bool):
        errors["user_id"] = ["must be an integer"]
    elif isinstance(raw_user_id, int):
        user_id = raw_user_id
    elif isinstance(raw_user_id, float) and raw_user_id.is_integer():
        user_id = int(raw_user_id)
    elif isinstance(raw_user_id, str) and raw_user_id.strip().isdigit():
        user_id = int(raw_user_id.strip())
    else:
        errors["user_id"] = ["must be an integer"]

    if user_id is not None and user_id < 1:
        errors["user_id"] = ["must be a positive integer"]

    if raw_original is None:
        errors["original_url"] = ["required"]
    elif not isinstance(raw_original, str):
        errors["original_url"] = ["must be a string"]
    elif not raw_original.strip():
        errors["original_url"] = ["must not be empty"]
    elif not _is_http_url(raw_original):
        errors["original_url"] = ["must be a valid http or https URL"]

    if raw_title is None:
        errors["title"] = ["required"]
    elif not isinstance(raw_title, str):
        errors["title"] = ["must be a string"]
    elif not raw_title.strip():
        errors["title"] = ["must not be empty"]

    if errors:
        return jsonify(error="validation failed", fields=errors), 400

    assert user_id is not None
    if User.get_or_none(User.id == user_id) is None:
        return jsonify(error="user not found"), 404

    original_url = raw_original.strip()
    title = raw_title.strip()
    now = datetime.now()
    url: Url | None = None

    for _ in range(_MAX_SHORT_CODE_ATTEMPTS):
        try:
            with db.atomic():
                max_id = Url.select(fn.MAX(Url.id)).scalar()
                next_id = (max_id or 0) + 1
                url = Url.create(
                    id=next_id,
                    user_id=user_id,
                    short_code=_generate_short_code(),
                    original_url=original_url,
                    title=title,
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )
            break
        except IntegrityError as exc:
            current_app.logger.warning(
                "create url retry after integrity error: %s", exc
            )

    if url is None:
        return jsonify(error="could not allocate a unique short code"), 503

    return jsonify(url_to_api_dict(url)), 201
