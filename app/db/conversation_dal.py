"""Conversation persistence DAL — CRUD for chat_conversations table."""

import json
from datetime import datetime
from typing import Dict, Any, Optional, List

from app.db.connection import get_db_connection, release_connection
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def save_conversation(
    conv_id: str,
    thread_id: str,
    title: str,
    messages: List[Dict[str, str]],
    created_at: datetime,
    updated_at: datetime,
) -> None:
    """Insert or update a conversation (UPSERT)."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO chat_conversations
                    (conv_id, thread_id, title, messages, created_at, updated_at)
                VALUES (%s, %s, %s, %s::jsonb, %s, %s)
                ON CONFLICT (conv_id) DO UPDATE SET
                    title      = EXCLUDED.title,
                    messages   = EXCLUDED.messages,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    conv_id,
                    thread_id,
                    title,
                    json.dumps(messages, ensure_ascii=False),
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("Failed to save conversation %s", conv_id)
        raise
    finally:
        release_connection(conn)


def update_conversation(
    conv_id: str,
    title: Optional[str] = None,
    messages: Optional[List[Dict[str, str]]] = None,
    updated_at: Optional[datetime] = None,
) -> None:
    """Update specific fields of an existing conversation."""
    sets: list[str] = []
    params: list[Any] = []

    if title is not None:
        sets.append("title = %s")
        params.append(title)
    if messages is not None:
        sets.append("messages = %s::jsonb")
        params.append(json.dumps(messages, ensure_ascii=False))
    if updated_at is not None:
        sets.append("updated_at = %s")
        params.append(updated_at)

    if not sets:
        return

    params.append(conv_id)
    sql = f"UPDATE chat_conversations SET {', '.join(sets)} WHERE conv_id = %s"

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("Failed to update conversation %s", conv_id)
        raise
    finally:
        release_connection(conn)


def load_all_conversations() -> Dict[str, Dict[str, Any]]:
    """Load all conversations from DB into the format expected by st.session_state.

    Returns:
        {conv_id: {"title", "messages", "thread_id", "created_at", "updated_at"}, ...}
    """
    from psycopg2.extras import RealDictCursor

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT conv_id, thread_id, title, messages, created_at, updated_at
                FROM chat_conversations
                ORDER BY updated_at DESC
                """
            )
            rows = cur.fetchall()
    except Exception:
        conn.rollback()
        logger.exception("Failed to load conversations")
        return {}
    finally:
        release_connection(conn)

    result: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        msgs = row["messages"]
        if isinstance(msgs, str):
            msgs = json.loads(msgs)

        result[row["conv_id"]] = {
            "title": row["title"],
            "messages": msgs,
            "thread_id": row["thread_id"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
    return result


def delete_conversation_db(conv_id: str) -> None:
    """Delete a conversation from the database."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM chat_conversations WHERE conv_id = %s",
                (conv_id,),
            )
            conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("Failed to delete conversation %s", conv_id)
        raise
    finally:
        release_connection(conn)
