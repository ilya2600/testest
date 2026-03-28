"""App configuration and constants (no Flask app instance)."""

import os
import re
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

TRENDING_LIKE_WEIGHT = 3.0
TRENDING_DECAY_PER_HOUR = 0.25
USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_]{3,32}$")
MAX_POST_CONTENT_LENGTH = 280
MAX_POST_IMAGE_BYTES = 300 * 1024
MAX_IMAGES_PER_POST = 4
MAX_IMAGE_URL_LENGTH = 1024
ALLOWED_IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}
PIXEL_ART_SIZE = 8
MAX_AVATAR_BYTES = 64 * 1024
AVATAR_MIME = "image/png"

IS_PRODUCTION = os.getenv("FLASK_ENV", "").lower() == "production"
DATABASE_PATH = str(BASE_DIR / os.getenv("DATABASE_PATH", "minisocial.db"))
REGISTRATION_ENABLED_DEFAULT = os.getenv("REGISTRATION_ENABLED_DEFAULT", "true").lower() in (
    "1",
    "true",
    "yes",
    "on",
)


def get_master_admin_credentials() -> tuple[str | None, str | None]:
    username = os.getenv("MASTER_ADMIN_USERNAME")
    password = os.getenv("MASTER_ADMIN_PASSWORD")
    if IS_PRODUCTION and (not username or not password):
        raise RuntimeError(
            "MASTER_ADMIN_USERNAME and MASTER_ADMIN_PASSWORD must be set in production."
        )
    return username, password


def parse_bool(text: str | None, default: bool = False) -> bool:
    if text is None:
        return default
    return text.lower() in ("1", "true", "yes", "on")


def build_flask_config() -> dict:
    secret_key = os.getenv("FLASK_SECRET_KEY")
    if not secret_key:
        if IS_PRODUCTION:
            raise RuntimeError("FLASK_SECRET_KEY must be set in production.")
        secret_key = "dev-secret-key-change-me"
    return {
        "IS_PRODUCTION": IS_PRODUCTION,
        "DATABASE_PATH": DATABASE_PATH,
        "REGISTRATION_ENABLED_DEFAULT": REGISTRATION_ENABLED_DEFAULT,
        "SECRET_KEY": secret_key,
    }
