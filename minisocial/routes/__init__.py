"""Register all HTTP routes on the Flask app."""


def register_routes(app):
    from minisocial.routes import accounts, admin, feed, media, posts

    feed.register_routes(app)
    media.register_routes(app)
    accounts.register_routes(app)
    admin.register_routes(app)
    posts.register_routes(app)
