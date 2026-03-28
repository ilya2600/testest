"""Create/delete posts and likes."""

from urllib.parse import urlparse

from flask import flash, jsonify, redirect, request, session, url_for

from minisocial import config
from minisocial.auth import current_user_can_manage_post, login_required
from minisocial.db import get_db_connection
from minisocial.services.feed import toggle_post_like


def register_routes(app):
    @app.route("/create-post", methods=["POST"])
    @login_required
    def create_post():
        content = request.form.get("content", "").strip()

        if not content:
            flash("Post cannot be empty.")
            return redirect(url_for("feed_newest"))
        if len(content) > config.MAX_POST_CONTENT_LENGTH:
            flash(f"Posts are limited to {config.MAX_POST_CONTENT_LENGTH} characters.")
            return redirect(url_for("feed_newest"))

        try:
            gallery_count = int(request.form.get("gallery_count", "0"))
        except ValueError:
            flash("Invalid gallery data.")
            return redirect(url_for("feed_newest"))

        gallery_count = max(0, min(config.MAX_IMAGES_PER_POST, gallery_count))

        gallery_rows: list[tuple[bytes | None, str | None, str | None]] = []
        for i in range(gallery_count):
            kind = request.form.get(f"gallery_slot_{i}_kind", "").strip().lower()
            if kind == "url":
                url = request.form.get(f"gallery_url_{i}", "").strip()
                if len(url) > config.MAX_IMAGE_URL_LENGTH:
                    flash("One of the image URLs is too long.")
                    return redirect(url_for("feed_newest"))
                parsed = urlparse(url)
                if parsed.scheme not in ("http", "https") or not parsed.netloc:
                    flash("Each image URL must start with http:// or https://")
                    return redirect(url_for("feed_newest"))
                gallery_rows.append((None, None, url))
            elif kind == "file":
                image_file = request.files.get(f"gallery_file_{i}")
                if not image_file or not image_file.filename:
                    flash("One of the image uploads is missing.")
                    return redirect(url_for("feed_newest"))
                image_mime = (image_file.mimetype or "").lower()
                if image_mime not in config.ALLOWED_IMAGE_MIME_TYPES:
                    allowed_types = ", ".join(sorted(config.ALLOWED_IMAGE_MIME_TYPES))
                    flash(f"Unsupported image type. Allowed: {allowed_types}.")
                    return redirect(url_for("feed_newest"))
                image_blob = image_file.read(config.MAX_POST_IMAGE_BYTES + 1)
                if not image_blob:
                    flash("One of the uploaded images is empty.")
                    return redirect(url_for("feed_newest"))
                if len(image_blob) > config.MAX_POST_IMAGE_BYTES:
                    flash(f"Each uploaded image must be at most {config.MAX_POST_IMAGE_BYTES // 1024} KB.")
                    return redirect(url_for("feed_newest"))
                gallery_rows.append((image_blob, image_mime, None))
            else:
                flash("Invalid gallery entry.")
                return redirect(url_for("feed_newest"))

        connection = get_db_connection()
        connection.execute(
            """
            INSERT INTO posts (
                content,
                author_id,
                author_name_snapshot,
                author_state,
                image_blob,
                image_mime,
                image_url
            )
            VALUES (?, ?, ?, 'active', NULL, NULL, NULL)
            """,
            (content, session["user_id"], session["username"]),
        )
        post_id = connection.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]

        for position, (blob, mime, url) in enumerate(gallery_rows):
            if url is not None:
                connection.execute(
                    """
                    INSERT INTO post_images (post_id, position, image_blob, image_mime, image_url)
                    VALUES (?, ?, NULL, NULL, ?)
                    """,
                    (post_id, position, url),
                )
            else:
                connection.execute(
                    """
                    INSERT INTO post_images (post_id, position, image_blob, image_mime, image_url)
                    VALUES (?, ?, ?, ?, NULL)
                    """,
                    (post_id, position, blob, mime),
                )

        connection.commit()
        connection.close()
        flash("Post published.")
        return redirect(url_for("feed_newest"))

    @app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
    @login_required
    def edit_post(post_id: int):
        flash("Editing posts is disabled.")
        return redirect(url_for("feed_newest"))

    @app.route("/delete-post/<int:post_id>", methods=["POST"])
    @login_required
    def delete_post(post_id: int):
        connection = get_db_connection()
        post = connection.execute(
            "SELECT id, author_id FROM posts WHERE id = ?",
            (post_id,),
        ).fetchone()
        if post is None:
            connection.close()
            flash("Post not found.")
            return redirect(url_for("feed_newest"))
        if not current_user_can_manage_post(post):
            connection.close()
            flash("You can only delete your own posts.")
            return redirect(url_for("feed_newest"))

        connection.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        connection.commit()
        connection.close()
        flash("Post deleted.")
        return redirect(url_for("feed_newest"))

    @app.route("/like-post/<int:post_id>", methods=["POST"])
    @login_required
    def like_post(post_id: int):
        connection = get_db_connection()
        post = connection.execute("SELECT id FROM posts WHERE id = ?", (post_id,)).fetchone()
        if post is None:
            connection.close()
            flash("Post not found.")
            return redirect(url_for("feed_newest"))

        user_id = session["user_id"]
        liked, _likes = toggle_post_like(connection, post_id, user_id)
        connection.commit()
        connection.close()
        flash("Post liked." if liked else "Like removed.")
        return redirect(url_for("feed_newest"))

    @app.route("/api/posts/<int:post_id>/like", methods=["POST"])
    @login_required
    def like_post_api(post_id: int):
        connection = get_db_connection()
        post = connection.execute("SELECT id FROM posts WHERE id = ?", (post_id,)).fetchone()
        if post is None:
            connection.close()
            return jsonify({"ok": False, "error": "Post not found."}), 404

        user_id = session["user_id"]
        liked, likes = toggle_post_like(connection, post_id, user_id)
        connection.commit()
        connection.close()
        return jsonify({"ok": True, "likes": likes, "liked": liked})
