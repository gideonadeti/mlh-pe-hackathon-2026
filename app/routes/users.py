from __future__ import annotations

from flask import Blueprint, jsonify, request
from peewee import IntegrityError, chunked

from app.database import db
from app.models import User
from app.services.user_csv import parse_users_csv_binary_stream

users_bp = Blueprint("users", __name__)

_BULK_FILE_KEYS = ("file", "users", "users_csv", "upload")
_INSERT_BATCH = 200


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
        return jsonify(error="database constraint violation", detail=str(exc)), 409

    return jsonify(imported=len(rows)), 201
