"""Template context processors."""

from flask import session

from minisocial import config
from minisocial.db import get_db_connection


def register_context_processors(app):
    @app.context_processor
    def inject_post_limits():
        return {
            "post_max_length": config.MAX_POST_CONTENT_LENGTH,
            "post_image_max_kb": config.MAX_POST_IMAGE_BYTES // 1024,
            "max_post_images": config.MAX_IMAGES_PER_POST,
        }

    @app.context_processor
    def inject_auth_data():
        uid = session.get("user_id")
        has_avatar = False
        if uid:
            connection = get_db_connection()
            row = connection.execute(
                "SELECT avatar_blob IS NOT NULL AS has_avatar FROM users WHERE id = ?",
                (uid,),
            ).fetchone()
            connection.close()
            has_avatar = bool(row and row["has_avatar"])
        return {
            "is_authenticated": bool(uid),
            "current_user_id": uid,
            "current_username": session.get("username"),
            "current_role": session.get("role"),
            "current_user_has_avatar": has_avatar,
        }
