import os

from dotenv import load_dotenv
from flask import Flask, abort, jsonify, redirect

from app.database import ensure_tables, init_db
from app.extensions import cache
from app.redirect_cache import get_redirect_target, set_redirect_target
from app.routes import register_routes


def create_app():
    load_dotenv()

    app = Flask(__name__)

    redis_url = os.environ.get("REDIS_URL", "").strip()
    if redis_url:
        app.config["CACHE_TYPE"] = "RedisCache"
        app.config["CACHE_REDIS_URL"] = redis_url
        app.config["CACHE_DEFAULT_TIMEOUT"] = int(
            os.environ.get("REDIRECT_CACHE_TIMEOUT", "300")
        )
        app.config["CACHE_KEY_PREFIX"] = "pe_"
    else:
        app.config["CACHE_TYPE"] = "NullCache"
        app.config["CACHE_NO_NULL_WARNING"] = True
    cache.init_app(app)

    init_db(app)

    from app import models  # noqa: F401 - registers models with Peewee

    ensure_tables()

    register_routes(app)

    @app.route("/health")
    def health():
        return jsonify(status="ok")

    @app.route("/<string:short_code>")
    def redirect_by_short_code(short_code: str):
        from app.models import Url

        cached = get_redirect_target(short_code)
        if cached is not None:
            response = redirect(cached, code=302)
            response.headers["X-Cache"] = "HIT"
            return response

        row = Url.get_or_none(Url.short_code == short_code)
        if row is None or not row.is_active:
            abort(404)

        set_redirect_target(short_code, row.original_url)
        response = redirect(row.original_url, code=302)
        response.headers["X-Cache"] = "MISS"
        return response

    return app
