from dotenv import load_dotenv
from flask import Flask, abort, jsonify, redirect

from app.database import init_db
from app.routes import register_routes


def create_app():
    load_dotenv()

    app = Flask(__name__)

    init_db(app)

    from app import models  # noqa: F401 - registers models with Peewee

    register_routes(app)

    @app.route("/health")
    def health():
        return jsonify(status="ok")

    @app.route("/<string:short_code>")
    def redirect_by_short_code(short_code: str):
        from app.models import Url

        row = Url.get_or_none(Url.short_code == short_code)
        if row is None or not row.is_active:
            abort(404)
        return redirect(row.original_url, code=302)

    return app
