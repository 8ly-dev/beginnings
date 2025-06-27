"""
Database operations for the blog demo application.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

# Global database connection for in-memory database
_db_conn: sqlite3.Connection | None = None


def init_database() -> None:
    """Initialize the SQLite in-memory database with required tables."""
    global _db_conn
    _db_conn = sqlite3.connect(":memory:", check_same_thread=False)
    
    _db_conn.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            author TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            published BOOLEAN DEFAULT 1
        )
    """)
    
    # Insert default posts
    default_posts = [
        (
            "Welcome to Beginnings",
            "This is our first blog post using the Beginnings framework! The framework provides a powerful yet simple way to build web applications with both HTML and API endpoints. It includes features like configuration-driven development, automatic API documentation, content-aware error handling, and an extension system for modular functionality.",
            "Admin",
            datetime.now().isoformat()
        ),
        (
            "Building Web Apps with Configuration",
            "Learn how to build web applications using configuration-driven development with the Beginnings framework. The framework allows you to define routes, middleware, and application behavior through YAML or JSON configuration files, making your applications more maintainable and flexible.",
            "Developer",
            datetime.now().isoformat()
        )
    ]
    
    _db_conn.executemany(
        "INSERT INTO posts (title, content, author, created_at) VALUES (?, ?, ?, ?)",
        default_posts
    )
    _db_conn.commit()


def get_all_posts() -> list[dict[str, Any]]:
    """Get all published posts from the database."""
    if not _db_conn:
        return []
    
    _db_conn.row_factory = sqlite3.Row
    cursor = _db_conn.execute(
        "SELECT * FROM posts WHERE published = 1 ORDER BY created_at DESC"
    )
    return [dict(row) for row in cursor.fetchall()]


def get_post_by_id(post_id: int) -> dict[str, Any] | None:
    """Get a specific post by ID."""
    if not _db_conn:
        return None
    
    _db_conn.row_factory = sqlite3.Row
    cursor = _db_conn.execute(
        "SELECT * FROM posts WHERE id = ? AND published = 1",
        (post_id,)
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def create_post(title: str, content: str, author: str) -> dict[str, Any]:
    """Create a new post in the database."""
    if not _db_conn:
        raise RuntimeError("Database not initialized")
    
    cursor = _db_conn.execute(
        "INSERT INTO posts (title, content, author, created_at) VALUES (?, ?, ?, ?)",
        (title, content, author, datetime.now().isoformat())
    )
    post_id = cursor.lastrowid
    _db_conn.commit()
    
    # Return the created post
    _db_conn.row_factory = sqlite3.Row
    cursor = _db_conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
    return dict(cursor.fetchone())


def delete_post(post_id: int) -> bool:
    """Delete a post from the database."""
    if not _db_conn:
        return False
    
    cursor = _db_conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    _db_conn.commit()
    return cursor.rowcount > 0