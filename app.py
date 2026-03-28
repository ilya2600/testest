"""
MiniSocial entry point. Application logic lives in the `minisocial` package.
"""

from minisocial import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
