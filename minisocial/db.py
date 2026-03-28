"""SQLite connection, schema, migrations, and init."""

import sqlite3

from flask import current_app
from werkzeug.security import generate_password_hash

from minisocial import config
from minisocial.config import get_master_admin_credentials


def get_db_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(current_app.config["DATABASE_PATH"])
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def column_exists(connection: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    columns = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(column["name"] == column_name for column in columns)


def validate_png_dimensions(data: bytes, width: int, height: int) -> bool:
    """Read width/height from PNG IHDR without external deps."""
    if len(data) < 24:
        return False
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return False
    if data[12:16] != b"IHDR":
        return False
    w = int.from_bytes(data[16:20], "big")
    h = int.from_bytes(data[20:24], "big")
    return w == width and h == height


def get_setting(connection: sqlite3.Connection, key: str) -> str | None:
    row = connection.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_setting(connection: sqlite3.Connection, key: str, value: str) -> None:
    connection.execute(
        """
        INSERT INTO app_settings (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )


def is_registration_enabled(connection: sqlite3.Connection) -> bool:
    value = get_setting(connection, "registration_enabled")
    if value is None:
        return bool(current_app.config["REGISTRATION_ENABLED_DEFAULT"])
    return config.parse_bool(value, bool(current_app.config["REGISTRATION_ENABLED_DEFAULT"]))


def create_base_tables(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            likes INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            status TEXT NOT NULL DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS post_likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(post_id, user_id)
        )
        """
    )


def migrate_posts_table(connection: sqlite3.Connection) -> None:
    if not column_exists(connection, "posts", "author_id"):
        connection.execute("ALTER TABLE posts ADD COLUMN author_id INTEGER")
    if not column_exists(connection, "posts", "author_name_snapshot"):
        connection.execute("ALTER TABLE posts ADD COLUMN author_name_snapshot TEXT")
    if not column_exists(connection, "posts", "author_state"):
        connection.execute("ALTER TABLE posts ADD COLUMN author_state TEXT DEFAULT 'active'")
    if not column_exists(connection, "posts", "content_backup"):
        connection.execute("ALTER TABLE posts ADD COLUMN content_backup TEXT")
    if not column_exists(connection, "posts", "image_blob"):
        connection.execute("ALTER TABLE posts ADD COLUMN image_blob BLOB")
    if not column_exists(connection, "posts", "image_mime"):
        connection.execute("ALTER TABLE posts ADD COLUMN image_mime TEXT")
    if not column_exists(connection, "posts", "image_url"):
        connection.execute("ALTER TABLE posts ADD COLUMN image_url TEXT")

    connection.execute(
        """
        UPDATE posts
        SET author_state = 'active'
        WHERE author_state IS NULL OR author_state = ''
        """
    )


def sync_post_like_counts(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        UPDATE posts
        SET likes = (
            SELECT COUNT(*)
            FROM post_likes
            WHERE post_likes.post_id = posts.id
        )
        WHERE EXISTS (
            SELECT 1
            FROM post_likes
            WHERE post_likes.post_id = posts.id
        )
        """
    )


def seed_app_settings(connection: sqlite3.Connection) -> None:
    if not table_exists(connection, "app_settings"):
        return
    if get_setting(connection, "registration_enabled") is None:
        default_value = "true" if current_app.config["REGISTRATION_ENABLED_DEFAULT"] else "false"
        set_setting(connection, "registration_enabled", default_value)


def migrate_roles(connection: sqlite3.Connection) -> None:
    connection.execute("UPDATE users SET role = 'master' WHERE role = 'master_admin'")


def migrate_users_table(connection: sqlite3.Connection) -> None:
    if not column_exists(connection, "users", "avatar_blob"):
        connection.execute("ALTER TABLE users ADD COLUMN avatar_blob BLOB")
    if not column_exists(connection, "users", "avatar_mime"):
        connection.execute("ALTER TABLE users ADD COLUMN avatar_mime TEXT")


def ensure_post_images_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS post_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            image_blob BLOB,
            image_mime TEXT,
            image_url TEXT,
            FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
            UNIQUE(post_id, position)
        )
        """
    )


def migrate_legacy_post_images(connection: sqlite3.Connection) -> None:
    if not table_exists(connection, "post_images"):
        return
    connection.execute(
        """
        INSERT INTO post_images (post_id, position, image_blob, image_mime, image_url)
        SELECT posts.id, 0, posts.image_blob, posts.image_mime, NULL
        FROM posts
        WHERE posts.image_blob IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM post_images pi WHERE pi.post_id = posts.id
          )
        """
    )
    connection.execute(
        """
        INSERT INTO post_images (post_id, position, image_blob, image_mime, image_url)
        SELECT posts.id, 0, NULL, NULL, posts.image_url
        FROM posts
        WHERE posts.image_url IS NOT NULL
          AND posts.image_blob IS NULL
          AND NOT EXISTS (
              SELECT 1 FROM post_images pi WHERE pi.post_id = posts.id
          )
        """
    )


def ensure_master_admin(connection: sqlite3.Connection) -> None:
    admin_exists = connection.execute("SELECT id FROM users WHERE role = 'master' LIMIT 1").fetchone()
    if admin_exists:
        return

    username, password = get_master_admin_credentials()
    if not username or not password:
        username = "admin"
        password = "admin12345"

    connection.execute(
        """
        INSERT INTO users (username, password_hash, role, status)
        VALUES (?, ?, 'master', 'active')
        """,
        (username, generate_password_hash(password)),
    )


def init_db() -> None:
    connection = get_db_connection()
    create_base_tables(connection)
    migrate_posts_table(connection)
    migrate_users_table(connection)
    ensure_post_images_table(connection)
    migrate_legacy_post_images(connection)
    migrate_roles(connection)
    seed_app_settings(connection)
    ensure_master_admin(connection)
    sync_post_like_counts(connection)
    connection.commit()
    connection.close()
