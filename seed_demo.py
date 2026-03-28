"""
Optional demo content seeder (fake users, avatars, posts, images, likes).

Enable with DEMO_SEED_ENABLED=true in .env, then run from this folder:
  python seed_demo.py

Safe to run multiple times: skips if already seeded unless DEMO_SEED_FORCE=true
(removes prior demo_seed_* users and re-runs).
"""

from __future__ import annotations

import os
import random
import sqlite3
import struct
import zlib
from pathlib import Path

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

USERNAME_PREFIX = "demo_seed_"
SETTING_KEY = "demo_seed_v1"
DEFAULT_USER_COUNT = 8
DEFAULT_PASSWORD = "DemoSeed123!"  # documented; change in production if you use demo accounts

# Short sample lines (feed-appropriate, <= 280 chars when combined)
SNIPPETS = [
    "Morning coffee and a quiet feed.",
    "Testing pixels, testing posts.",
    "Anyone else on minisocial today?",
    "Dropped a new 8×8 in the editor.",
    "Lurking, liking, repeating.",
    "Hello from the demo seed script.",
    "Random thought: tabs or spaces?",
    "Another line in the SQLite.",
    "Trending or newest — both are fun.",
    "Ship it, then fix it.",
]


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def _chunk(tag: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(tag + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)


def png_rgba(width: int, height: int, rgba: bytes) -> bytes:
    """Minimal RGBA PNG (no external deps)."""
    if len(rgba) != width * height * 4:
        raise ValueError("rgba length mismatch")
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">2I5B", width, height, 8, 6, 0, 0, 0)
    raw = b""
    row = width * 4
    for y in range(height):
        raw += b"\x00" + rgba[y * row : (y + 1) * row]
    compressed = zlib.compress(raw, 9)
    return sig + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", compressed) + _chunk(b"IEND", b"")


def random_rgba(width: int, height: int) -> bytes:
    return bytes(random.getrandbits(8) for _ in range(width * height * 4))


def random_avatar_png() -> bytes:
    return png_rgba(8, 8, random_rgba(8, 8))


def random_post_png() -> tuple[bytes, str]:
    """Return (blob, mime) within typical upload limits."""
    w = random.choice((8, 16, 24, 32))
    h = w
    mime = "image/png"
    return png_rgba(w, h, random_rgba(w, h)), mime


def _clear_demo_users(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        DELETE FROM post_likes WHERE post_id IN (
            SELECT id FROM posts WHERE author_id IN (
                SELECT id FROM users WHERE username LIKE ?
            )
        )
        """,
        (USERNAME_PREFIX + "%",),
    )
    connection.execute(
        """
        DELETE FROM post_likes WHERE user_id IN (
            SELECT id FROM users WHERE username LIKE ?
        )
        """,
        (USERNAME_PREFIX + "%",),
    )
    connection.execute(
        """
        DELETE FROM post_images WHERE post_id IN (
            SELECT id FROM posts WHERE author_id IN (
                SELECT id FROM users WHERE username LIKE ?
            )
        )
        """,
        (USERNAME_PREFIX + "%",),
    )
    connection.execute(
        """
        DELETE FROM posts WHERE author_id IN (
            SELECT id FROM users WHERE username LIKE ?
        )
        """,
        (USERNAME_PREFIX + "%",),
    )
    connection.execute(
        "DELETE FROM users WHERE username LIKE ?",
        (USERNAME_PREFIX + "%",),
    )


def main() -> None:
    enabled = os.getenv("DEMO_SEED_ENABLED", "").lower() in ("1", "true", "yes", "on")
    if not enabled:
        print("DEMO_SEED_ENABLED is not set to true; skipping demo seed.")
        raise SystemExit(0)

    from minisocial import create_app
    from minisocial import config
    from minisocial.db import get_db_connection, init_db, sync_post_like_counts

    flask_app = create_app()

    with flask_app.app_context():
        init_db()
        connection = get_db_connection()

        force = os.getenv("DEMO_SEED_FORCE", "").lower() in ("1", "true", "yes", "on")
        row = connection.execute(
            "SELECT value FROM app_settings WHERE key = ?",
            (SETTING_KEY,),
        ).fetchone()
        already = row and row["value"] == "1"

        if already and not force:
            print("Demo seed already applied (see app_settings). Set DEMO_SEED_FORCE=true to replace demo users.")
            connection.close()
            raise SystemExit(0)

        leftover = connection.execute(
            "SELECT COUNT(*) AS c FROM users WHERE username LIKE ?",
            (USERNAME_PREFIX + "%",),
        ).fetchone()["c"]
        if leftover and not force and not already:
            print(
                f"Found {leftover} leftover {USERNAME_PREFIX}* user(s) (incomplete run). "
                "Set DEMO_SEED_FORCE=true to remove them and seed again."
            )
            connection.close()
            raise SystemExit(1)

        if force:
            print("Removing previous demo_seed_* users and their posts…")
            _clear_demo_users(connection)
            connection.execute("DELETE FROM app_settings WHERE key = ?", (SETTING_KEY,))
            connection.commit()

        n_users = _env_int("DEMO_SEED_USERS", DEFAULT_USER_COUNT)
        if n_users < 2:
            print("DEMO_SEED_USERS must be at least 2 for likes between users. Using 2.")
            n_users = 2

        random.seed()
        pwd_hash = generate_password_hash(DEFAULT_PASSWORD)
        user_ids: list[int] = []

        for i in range(n_users):
            username = f"{USERNAME_PREFIX}{i:02d}"
            try:
                connection.execute(
                    """
                    INSERT INTO users (username, password_hash, role, status, avatar_blob, avatar_mime)
                    VALUES (?, ?, 'user', 'active', ?, ?)
                    """,
                    (username, pwd_hash, random_avatar_png(), config.AVATAR_MIME),
                )
            except sqlite3.IntegrityError:
                connection.rollback()
                connection.close()
                print(f"Username {username!r} already exists (non-demo). Abort.")
                raise SystemExit(1)
            uid = connection.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
            user_ids.append(int(uid))

        post_ids: list[int] = []
        for uid in user_ids:
            uname_row = connection.execute(
                "SELECT username FROM users WHERE id = ?",
                (uid,),
            ).fetchone()
            uname = uname_row["username"]
            n_posts = random.randint(2, 5)
            for _ in range(n_posts):
                parts = [random.choice(SNIPPETS)]
                if random.random() < 0.4:
                    parts.append(random.choice(SNIPPETS))
                content = " ".join(parts)[: config.MAX_POST_CONTENT_LENGTH]

                connection.execute(
                    """
                    INSERT INTO posts (
                        content, author_id, author_name_snapshot, author_state,
                        image_blob, image_mime, image_url
                    )
                    VALUES (?, ?, ?, 'active', NULL, NULL, NULL)
                    """,
                    (content, uid, uname),
                )
                pid = connection.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
                pid = int(pid)
                post_ids.append(pid)

                n_img = random.randint(0, config.MAX_IMAGES_PER_POST)
                for pos in range(n_img):
                    blob, mime = random_post_png()
                    if len(blob) > config.MAX_POST_IMAGE_BYTES:
                        blob, mime = random_avatar_png(), config.AVATAR_MIME
                    connection.execute(
                        """
                        INSERT INTO post_images (post_id, position, image_blob, image_mime, image_url)
                        VALUES (?, ?, ?, ?, NULL)
                        """,
                        (pid, pos, blob, mime),
                    )

        for pid in post_ids:
            row = connection.execute(
                "SELECT author_id FROM posts WHERE id = ?",
                (pid,),
            ).fetchone()
            if not row:
                continue
            author_id = row["author_id"]
            candidates = [u for u in user_ids if u != author_id]
            random.shuffle(candidates)
            cap = min(len(candidates), max(1, len(user_ids) // 2))
            k = random.randint(0, cap)
            for liker in candidates[:k]:
                try:
                    connection.execute(
                        "INSERT INTO post_likes (post_id, user_id) VALUES (?, ?)",
                        (pid, liker),
                    )
                    connection.execute(
                        "UPDATE posts SET likes = likes + 1 WHERE id = ?",
                        (pid,),
                    )
                except sqlite3.IntegrityError:
                    pass

        sync_post_like_counts(connection)

        connection.execute(
            """
            INSERT INTO app_settings (key, value)
            VALUES (?, '1')
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (SETTING_KEY,),
        )
        connection.commit()

        last_suffix = f"{n_users - 1:02d}"
        print(
            f"Demo seed complete: {n_users} users ({USERNAME_PREFIX}00 … {USERNAME_PREFIX}{last_suffix}), "
            f"password for all: {DEFAULT_PASSWORD!r}, "
            f"{len(post_ids)} posts, random likes."
        )
        connection.close()


if __name__ == "__main__":
    main()
