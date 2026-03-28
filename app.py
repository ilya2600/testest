"""
MiniSocial entry point. Application logic lives in the `minisocial` package.
"""

from minisocial import create_app
from minisocial.db import init_db

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(debug=True)
