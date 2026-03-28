"""Admin panel and user management."""

from flask import flash, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash

from minisocial import config
from minisocial.auth import admin_or_master_required, master_required
from minisocial.db import get_db_connection, is_registration_enabled, set_setting
from minisocial.services.feed import count_master_accounts


def register_routes(app):
    @app.route("/admin")
    @admin_or_master_required
    def admin_panel():
        connection = get_db_connection()
        users = connection.execute(
            """
            SELECT id, username, role, status, created_at
            FROM users
            ORDER BY
                CASE role
                    WHEN 'master' THEN 0
                    WHEN 'admin' THEN 1
                    ELSE 2
                END,
                username ASC
            """
        ).fetchall()
        registration_enabled = is_registration_enabled(connection)
        connection.close()
        return render_template(
            "admin.html",
            users=users,
            registration_enabled=registration_enabled,
            can_manage_master_controls=(session.get("role") == "master"),
        )

    @app.route("/admin/toggle-registration", methods=["POST"])
    @master_required
    def toggle_registration():
        action = request.form.get("action", "").strip().lower()
        if action not in ("on", "off"):
            flash("Invalid registration toggle action.")
            return redirect(url_for("admin_panel"))

        value = "true" if action == "on" else "false"
        connection = get_db_connection()
        set_setting(connection, "registration_enabled", value)
        connection.commit()
        connection.close()
        flash(f"Public registration turned {action}.")
        return redirect(url_for("admin_panel"))

    @app.route("/admin/create-user", methods=["POST"])
    @master_required
    def admin_create_user():
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "user").strip()
        if role not in ("user", "admin"):
            role = "user"

        if not config.USERNAME_PATTERN.match(username):
            flash("Username must be 3-32 chars: letters, numbers, underscore only.")
            return redirect(url_for("admin_panel"))
        if len(password) < 8:
            flash("Password must be at least 8 characters long.")
            return redirect(url_for("admin_panel"))

        connection = get_db_connection()
        existing_user = connection.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if existing_user:
            connection.close()
            flash("Username already exists.")
            return redirect(url_for("admin_panel"))

        connection.execute(
            """
            INSERT INTO users (username, password_hash, role, status)
            VALUES (?, ?, ?, 'active')
            """,
            (username, generate_password_hash(password), role),
        )
        connection.commit()
        connection.close()
        flash("User created from admin panel.")
        return redirect(url_for("admin_panel"))

    @app.route("/admin/users/<int:user_id>/archive", methods=["POST"])
    @admin_or_master_required
    def archive_user(user_id: int):
        if user_id == session.get("user_id"):
            flash("You cannot archive your own account.")
            return redirect(url_for("admin_panel"))

        connection = get_db_connection()
        target_user = connection.execute(
            "SELECT id, role, status FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if target_user is None:
            connection.close()
            flash("User not found.")
            return redirect(url_for("admin_panel"))

        actor_role = session.get("role")
        if target_user["role"] == "master":
            connection.close()
            flash("Master account cannot be archived.")
            return redirect(url_for("admin_panel"))
        if actor_role == "admin" and target_user["role"] != "user":
            connection.close()
            flash("Admins can only archive regular users.")
            return redirect(url_for("admin_panel"))
        if target_user["role"] == "admin" and actor_role != "master":
            connection.close()
            flash("Only master can archive admin accounts.")
            return redirect(url_for("admin_panel"))
        if target_user["role"] == "master" and count_master_accounts(connection) <= 1:
            connection.close()
            flash("Cannot archive the last master account.")
            return redirect(url_for("admin_panel"))

        connection.execute(
            "UPDATE users SET status = 'archived', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (user_id,),
        )
        connection.execute(
            """
            UPDATE posts
            SET content_backup = CASE
                    WHEN content_backup IS NULL THEN content
                    ELSE content_backup
                END,
                content = 'post from deleted user',
                author_state = 'archived'
            WHERE author_id = ?
            """,
            (user_id,),
        )
        connection.commit()
        connection.close()
        flash("User archived.")
        return redirect(url_for("admin_panel"))

    @app.route("/admin/users/<int:user_id>/restore", methods=["POST"])
    @admin_or_master_required
    def restore_user(user_id: int):
        connection = get_db_connection()
        target_user = connection.execute(
            "SELECT id, role FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if target_user is None:
            connection.close()
            flash("User not found.")
            return redirect(url_for("admin_panel"))

        actor_role = session.get("role")
        if target_user["role"] == "master":
            connection.close()
            flash("Master account cannot be modified here.")
            return redirect(url_for("admin_panel"))
        if actor_role == "admin" and target_user["role"] != "user":
            connection.close()
            flash("Admins can only restore regular users.")
            return redirect(url_for("admin_panel"))
        if target_user["role"] == "admin" and actor_role != "master":
            connection.close()
            flash("Only master can restore admin accounts.")
            return redirect(url_for("admin_panel"))

        connection.execute(
            "UPDATE users SET status = 'active', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (user_id,),
        )
        connection.execute(
            """
            UPDATE posts
            SET content = CASE
                    WHEN content_backup IS NOT NULL THEN content_backup
                    ELSE content
                END,
                content_backup = NULL,
                author_state = 'active'
            WHERE author_id = ?
              AND author_state = 'archived'
            """,
            (user_id,),
        )
        connection.commit()
        connection.close()
        flash("User restored.")
        return redirect(url_for("admin_panel"))

    @app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
    @admin_or_master_required
    def delete_user(user_id: int):
        if session.get("role") == "admin":
            flash("Only master can delete accounts.")
            return redirect(url_for("admin_panel"))

        if user_id == session.get("user_id"):
            flash("You cannot delete your own account.")
            return redirect(url_for("admin_panel"))

        connection = get_db_connection()
        target_user = connection.execute(
            "SELECT id, role FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if target_user is None:
            connection.close()
            flash("User not found.")
            return redirect(url_for("admin_panel"))

        actor_role = session.get("role")
        if target_user["role"] == "master":
            connection.close()
            flash("Master account cannot be deleted.")
            return redirect(url_for("admin_panel"))
        if target_user["role"] == "admin" and actor_role != "master":
            connection.close()
            flash("Only master can delete admin accounts.")
            return redirect(url_for("admin_panel"))
        if target_user["role"] == "master" and count_master_accounts(connection) <= 1:
            connection.close()
            flash("Cannot delete the last master account.")
            return redirect(url_for("admin_panel"))

        connection.execute(
            """
            UPDATE posts
            SET content = 'post from deleted user',
                content_backup = NULL,
                author_id = NULL,
                author_state = 'deleted',
                author_name_snapshot = 'user deleted'
            WHERE author_id = ?
            """,
            (user_id,),
        )
        connection.execute("DELETE FROM users WHERE id = ?", (user_id,))
        connection.commit()
        connection.close()
        flash("User permanently deleted.")
        return redirect(url_for("admin_panel"))
