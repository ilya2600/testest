"""Feed index and redirects."""

from flask import redirect, render_template, url_for

from minisocial.services.feed import fetch_posts


def register_routes(app):
    @app.route("/")
    def index():
        return redirect(url_for("feed_newest"))

    @app.route("/feed/newest")
    def feed_newest():
        posts = fetch_posts("newest")
        return render_template("index.html", posts=posts, feed_type="newest")

    @app.route("/feed/trending")
    def feed_trending():
        posts = fetch_posts("trending")
        return render_template("index.html", posts=posts, feed_type="trending")
