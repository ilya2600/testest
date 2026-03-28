"""Session auth decorators and post permission helpers."""

import sqlite3
from functools import wraps

from flask import flash, redirect, session, url_for

from minisocial.db import get_db_connection


def _require_active_session_user():
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in first.")
        return None, redirect(url_for("login"))

    connection = get_db_connection()
    user = connection.execute(
        "SELECT id, username, role, status FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    connection.close()

    if user is None:
        session.clear()
        flash("Your session is no longer valid. Please log in again.")
        return None, redirect(url_for("login"))

    if user["status"] != "active":
        session.clear()
        flash("Your account is archived. Contact administrator.")
        return None, redirect(url_for("login"))

    session["username"] = user["username"]
    session["role"] = user["role"]
    return user, None


def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        _, error_response = _require_active_session_user()
        if error_response is not None:
            return error_response
        return view_func(*args, **kwargs)

    return wrapped_view


def admin_or_master_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        user, error_response = _require_active_session_user()
        if error_response is not None:
            return error_response
        if user["role"] not in ("admin", "master"):
            flash("Access denied.")
            return redirect(url_for("feed_newest"))
        return view_func(*args, **kwargs)

    return wrapped_view


def master_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        user, error_response = _require_active_session_user()
        if error_response is not None:
            return error_response
        if user["role"] != "master":
            flash("Only master account can perform this action.")
            return redirect(url_for("admin_panel"))
        return view_func(*args, **kwargs)

    return wrapped_view


def current_user_can_manage_post(post: sqlite3.Row) -> bool:
    if session.get("role") in ("admin", "master"):
        return True
    user_id = session.get("user_id")
    if not user_id:
        return False
    return post["author_id"] == user_id
