"""Avatars and post gallery image bytes."""

from flask import Response, flash, redirect, request, session, url_for

from minisocial import config
from minisocial.auth import login_required
from minisocial.db import get_db_connection, validate_png_dimensions


def register_routes(app):
    @app.route("/user-avatar/<int:user_id>")
    def user_avatar(user_id: int):
        connection = get_db_connection()
        row = connection.execute(
            """
            SELECT avatar_blob, avatar_mime, status
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()
        connection.close()

        if row is None or row["avatar_blob"] is None or row["status"] != "active":
            return ("", 404)

        mime = (row["avatar_mime"] or config.AVATAR_MIME).lower()
        if mime != "image/png":
            return ("", 404)

        return Response(
            row["avatar_blob"],
            mimetype=config.AVATAR_MIME,
            headers={"Cache-Control": "private, no-cache"},
        )

    @app.route("/profile/avatar", methods=["POST"])
    @login_required
    def save_avatar():
        avatar_file = request.files.get("avatar_file")
        if not avatar_file or not avatar_file.filename:
            flash("No avatar image uploaded.")
            return redirect(url_for("feed_newest"))

        mime = (avatar_file.mimetype or "").lower()
        if mime != "image/png":
            flash("Avatar must be a PNG.")
            return redirect(url_for("feed_newest"))

        data = avatar_file.read(config.MAX_AVATAR_BYTES + 1)
        if not data:
            flash("Avatar file is empty.")
            return redirect(url_for("feed_newest"))
        if len(data) > config.MAX_AVATAR_BYTES:
            flash("Avatar file is too large.")
            return redirect(url_for("feed_newest"))
        if not validate_png_dimensions(data, config.PIXEL_ART_SIZE, config.PIXEL_ART_SIZE):
            flash(f"Avatar must be a {config.PIXEL_ART_SIZE}×{config.PIXEL_ART_SIZE} PNG.")
            return redirect(url_for("feed_newest"))

        connection = get_db_connection()
        connection.execute(
            """
            UPDATE users
            SET avatar_blob = ?, avatar_mime = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (data, config.AVATAR_MIME, session["user_id"]),
        )
        connection.commit()
        connection.close()
        flash("Profile picture saved.")
        return redirect(url_for("feed_newest"))

    @app.route("/post-image/<int:post_id>/<int:slot>")
    def post_gallery_image(post_id: int, slot: int):
        if slot < 0 or slot >= config.MAX_IMAGES_PER_POST:
            return ("", 404)
        connection = get_db_connection()
        row = connection.execute(
            """
            SELECT post_images.image_blob, post_images.image_mime, posts.author_state
            FROM post_images
            JOIN posts ON posts.id = post_images.post_id
            WHERE post_images.post_id = ?
              AND post_images.position = ?
            """,
            (post_id, slot),
        ).fetchone()
        connection.close()

        if (
            row is None
            or row["image_blob"] is None
            or (row["image_mime"] or "").lower() not in config.ALLOWED_IMAGE_MIME_TYPES
            or row["author_state"] != "active"
        ):
            return ("", 404)

        return Response(
            row["image_blob"],
            mimetype=row["image_mime"],
            headers={"Cache-Control": "public, max-age=3600"},
        )
