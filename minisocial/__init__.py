"""MiniSocial Flask application factory."""

from pathlib import Path

from flask import Flask

from minisocial.config import build_flask_config
from minisocial.context import register_context_processors
from minisocial.routes import register_routes


def create_app() -> Flask:
    base_dir = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        template_folder=str(base_dir / "templates"),
        static_folder=str(base_dir / "static"),
    )
    app.config.update(build_flask_config())

    register_context_processors(app)
    register_routes(app)

    return app
