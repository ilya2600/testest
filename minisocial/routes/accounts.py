"""Login, logout, registration."""

from flask import flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from minisocial import config
from minisocial.auth import login_required
from minisocial.db import get_db_connection, is_registration_enabled


def register_routes(app):
    @app.route("/register", methods=["GET", "POST"])
    def register():
        connection = get_db_connection()
        registration_open = is_registration_enabled(connection)

        if request.method == "POST":
            if not registration_open:
                connection.close()
                flash("Registration is currently disabled.")
                return redirect(url_for("login"))

            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()

            if not config.USERNAME_PATTERN.match(username):
                connection.close()
                flash("Username must be 3-32 chars: letters, numbers, underscore only.")
                return render_template("register.html", registration_open=registration_open)
            if len(password) < 8:
                connection.close()
                flash("Password must be at least 8 characters long.")
                return render_template("register.html", registration_open=registration_open)

            existing_user = connection.execute(
                "SELECT id FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if existing_user:
                connection.close()
                flash("Username already exists.")
                return render_template("register.html", registration_open=registration_open)

            connection.execute(
                """
                INSERT INTO users (username, password_hash, role, status)
                VALUES (?, ?, 'user', 'active')
                """,
                (username, generate_password_hash(password)),
            )
            connection.commit()
            connection.close()
            flash("Registration successful. Please log in.")
            return redirect(url_for("login"))

        connection.close()
        return render_template("register.html", registration_open=registration_open)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()

            connection = get_db_connection()
            user = connection.execute(
                """
                SELECT id, username, password_hash, role, status
                FROM users
                WHERE username = ?
                """,
                (username,),
            ).fetchone()
            connection.close()

            if user is None or not check_password_hash(user["password_hash"], password):
                flash("Invalid username or password.")
                return render_template("login.html")
            if user["status"] != "active":
                flash("Your account is archived. Contact administrator.")
                return render_template("login.html")

            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            flash("Welcome back.")
            return redirect(url_for("feed_newest"))

        return render_template("login.html")

    @app.route("/logout", methods=["POST"])
    @login_required
    def logout():
        session.clear()
        flash("Logged out.")
        return redirect(url_for("login"))
