from __future__ import annotations

from datetime import datetime

from flask import Blueprint, current_app, jsonify, request
from peewee import IntegrityError, chunked, fn

from app.database import db
from app.models import User
from app.services.user_csv import parse_users_csv_binary_stream, user_to_api_dict

users_bp = Blueprint("users", __name__)

_BULK_FILE_KEYS = ("file", "users", "users_csv", "upload")
_INSERT_BATCH = 200
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


def _first_uploaded_file():
    for key in _BULK_FILE_KEYS:
        if key not in request.files:
            continue
        storage = request.files[key]
        if storage and storage.filename:
            return storage
    for storage in request.files.values():
        if storage and storage.filename:
            return storage
    return None


@users_bp.route("/users", methods=["GET"])
def list_users():
    base = User.select().order_by(User.id)
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
        total = int(base.count())
        total_pages = (total + per_page - 1) // per_page if total else 0
        offset = (page - 1) * per_page
        rows = base.offset(offset).limit(per_page)
        payload = [user_to_api_dict(u) for u in rows]
        has_next = total_pages > 0 and page < total_pages
        has_prev = page > 1
        return jsonify(
            users=payload,
            page=page,
            per_page=per_page,
            total=total,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev,
        )

    payload = [user_to_api_dict(u) for u in base]
    return jsonify(payload)


@users_bp.route("/users", methods=["POST"])
def create_user():
    body = request.get_json(silent=True)
    if body is None or not isinstance(body, dict):
        return jsonify(error="JSON object required"), 400

    errors: dict[str, list[str]] = {}
    raw_username = body.get("username")
    raw_email = body.get("email")

    if raw_username is None:
        errors["username"] = ["required"]
    elif not isinstance(raw_username, str):
        errors["username"] = ["must be a string"]
    elif not raw_username.strip():
        errors["username"] = ["must not be empty"]

    if raw_email is None:
        errors["email"] = ["required"]
    elif not isinstance(raw_email, str):
        errors["email"] = ["must be a string"]
    elif not raw_email.strip():
        errors["email"] = ["must not be empty"]

    if errors:
        return jsonify(error="validation failed", fields=errors), 400

    username = raw_username.strip()
    email = raw_email.strip()

    try:
        with db.atomic():
            max_id = User.select(fn.MAX(User.id)).scalar()
            next_id = (max_id or 0) + 1
            user = User.create(
                id=next_id,
                username=username,
                email=email,
                created_at=datetime.now(),
            )
    except IntegrityError:
        current_app.logger.warning(
            "create user integrity error (likely duplicate email)"
        )
        return jsonify(error="email already exists"), 409

    return jsonify(user_to_api_dict(user)), 201


@users_bp.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id: int):
    try:
        user = User.get_by_id(user_id)
    except User.DoesNotExist:
        return jsonify(error="user not found"), 404
    return jsonify(user_to_api_dict(user))


@users_bp.route("/users/bulk", methods=["POST"])
def bulk_import_users():
    upload = _first_uploaded_file()
    if upload is None:
        return jsonify(error="expected multipart file upload (e.g. field 'file')"), 400

    try:
        upload.stream.seek(0)
        rows = parse_users_csv_binary_stream(upload.stream)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400

    if not rows:
        return jsonify(imported=0), 201

    try:
        with db.atomic():
            for batch in chunked(rows, _INSERT_BATCH):
                User.insert_many(batch).execute()
    except IntegrityError as exc:
        current_app.logger.warning("users/bulk integrity error: %s", exc)
        return (
            jsonify(
                error="Import conflicts with existing data (duplicate id, email, or other database constraint).",
            ),
            409,
        )

    return jsonify(imported=len(rows)), 201
