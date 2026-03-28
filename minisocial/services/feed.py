"""Feed queries and like toggling."""

import sqlite3

from flask import session

from minisocial import config
from minisocial.db import get_db_connection


def count_master_accounts(connection: sqlite3.Connection) -> int:
    row = connection.execute("SELECT COUNT(*) AS total FROM users WHERE role = 'master'").fetchone()
    return row["total"]


def toggle_post_like(connection: sqlite3.Connection, post_id: int, user_id: int) -> tuple[bool, int]:
    existing_like = connection.execute(
        "SELECT id FROM post_likes WHERE post_id = ? AND user_id = ?",
        (post_id, user_id),
    ).fetchone()

    if existing_like:
        connection.execute(
            "DELETE FROM post_likes WHERE post_id = ? AND user_id = ?",
            (post_id, user_id),
        )
        connection.execute(
            "UPDATE posts SET likes = CASE WHEN likes > 0 THEN likes - 1 ELSE 0 END WHERE id = ?",
            (post_id,),
        )
        likes_row = connection.execute("SELECT likes FROM posts WHERE id = ?", (post_id,)).fetchone()
        return False, likes_row["likes"] if likes_row else 0

    connection.execute(
        "INSERT INTO post_likes (post_id, user_id) VALUES (?, ?)",
        (post_id, user_id),
    )
    connection.execute("UPDATE posts SET likes = likes + 1 WHERE id = ?", (post_id,))
    likes_row = connection.execute("SELECT likes FROM posts WHERE id = ?", (post_id,)).fetchone()
    return True, likes_row["likes"] if likes_row else 0


def attach_post_galleries(posts: list[sqlite3.Row]) -> list[dict]:
    """Attach up to four gallery image metadata rows per post (no blob bytes in feed query)."""
    if not posts:
        return []
    ids = [p["id"] for p in posts]
    connection = get_db_connection()
    placeholders = ",".join("?" * len(ids))
    rows = connection.execute(
        f"""
        SELECT post_id, position, image_blob IS NOT NULL AS has_blob, image_url, image_mime
        FROM post_images
        WHERE post_id IN ({placeholders})
        ORDER BY post_id, position
        """,
        ids,
    ).fetchall()
    connection.close()
    by_post: dict[int, list[dict[str, object]]] = {}
    for row in rows:
        pid = row["post_id"]
        by_post.setdefault(pid, []).append(
            {
                "position": row["position"],
                "has_blob": bool(row["has_blob"]),
                "image_url": row["image_url"],
                "image_mime": row["image_mime"],
            }
        )
    out: list[dict] = []
    for p in posts:
        d = dict(p)
        d["gallery"] = by_post.get(p["id"], [])
        out.append(d)
    return out


def fetch_posts(feed_type: str) -> list[dict]:
    connection = get_db_connection()
    current_user_id = session.get("user_id")
    base_sql = """
        SELECT
            posts.id,
            posts.content,
            posts.likes,
            posts.created_at,
            posts.updated_at,
            posts.author_id,
            posts.author_name_snapshot,
            posts.author_state,
            CASE WHEN users.avatar_blob IS NULL THEN 0 ELSE 1 END AS author_has_avatar,
            users.username AS author_username,
            CASE WHEN user_likes.id IS NULL THEN 0 ELSE 1 END AS liked_by_current_user
        FROM posts
        LEFT JOIN users ON users.id = posts.author_id
        LEFT JOIN post_likes AS user_likes
            ON user_likes.post_id = posts.id
           AND user_likes.user_id = ?
    """

    if feed_type == "trending":
        posts = connection.execute(
            f"""
            SELECT feed_data.*,
                   ROUND(
                       (feed_data.likes * ?) -
                       ((julianday('now') - julianday(feed_data.created_at)) * 24 * ?),
                       2
                   ) AS trending_score
            FROM ({base_sql}) AS feed_data
            ORDER BY trending_score DESC, created_at DESC, id DESC
            """,
            (
                config.TRENDING_LIKE_WEIGHT,
                config.TRENDING_DECAY_PER_HOUR,
                current_user_id,
            ),
        ).fetchall()
    else:
        posts = connection.execute(
            f"""
            SELECT feed_data.*, NULL AS trending_score
            FROM ({base_sql}) AS feed_data
            ORDER BY created_at DESC, id DESC
            """,
            (current_user_id,),
        ).fetchall()

    connection.close()
    return attach_post_galleries(posts)
