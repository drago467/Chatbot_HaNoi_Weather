"""ConversationState — thread-safe multi-turn router context.

Lưu trữ history dạng list các cặp ``(user_msg, assistant_json_4keys)`` khớp đúng
với schema training ``data/router/multitask_train.jsonl``::

    {
        "history": [{"user": ..., "assistant": "<json 4 keys>"}],
        "input": ...,
        "output": {"intent", "scope", "confidence", "rewritten_query"}
    }

Inference build ChatML messages (`/api/chat`) từ history + system prompt + user
query mới — model đã được train trên đúng cấu trúc đó nên đọc trực tiếp
``rewritten_query`` của assistant turn trước để giữ nguyên anchor (location +
time) thay vì cần class extract location từ tool output.

Sliding window K=3 đủ phủ ≥95% follow-up weather trong khi giữ token budget
~3k chars. TTL 60 phút bao quát planning kéo dài cả buổi sáng/chiều.
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field


_TTL_SECONDS = int(os.getenv("CONVERSATION_TTL_SECONDS", "3600"))
_K_WINDOW = 3


@dataclass
class ConversationState:
    """Per-thread router context — multi-turn ChatML format (v7.1)."""

    history: list[tuple[str, str]] = field(default_factory=list)
    turn_count: int = 0
    updated_at: float = field(default_factory=time.time)

    def to_messages(self, system_prompt: str, current_user: str) -> list[dict]:
        """Build ChatML messages array gửi Ollama ``/api/chat``.

        Trả về dạng ``[{role, content}, ...]`` với:
        - 1 system message
        - tối đa K_WINDOW cặp (user, assistant_json_4keys) từ history
        - 1 user message hiện tại
        """
        msgs: list[dict] = [{"role": "system", "content": system_prompt}]
        for user_msg, asst_json in self.history[-_K_WINDOW:]:
            msgs.append({"role": "user", "content": user_msg})
            msgs.append({"role": "assistant", "content": asst_json})
        msgs.append({"role": "user", "content": current_user})
        return msgs

    def record_turn(self, user_msg: str, assistant_json: str) -> None:
        """Append cặp (user, assistant_json_4keys) vào history với sliding K=3."""
        self.history.append((user_msg, assistant_json))
        if len(self.history) > _K_WINDOW:
            self.history = self.history[-_K_WINDOW:]
        self.turn_count += 1
        self.updated_at = time.time()


class ConversationStateStore:
    """Thread-safe in-memory store với TTL. Không persist qua restart."""

    def __init__(self, ttl_seconds: int = _TTL_SECONDS):
        self._store: dict[str, ConversationState] = {}
        self._lock = threading.Lock()
        self._ttl = ttl_seconds

    def get(self, thread_id: str) -> ConversationState | None:
        with self._lock:
            state = self._store.get(thread_id)
            if state is None:
                return None
            if time.time() - state.updated_at > self._ttl:
                del self._store[thread_id]
                return None
            return state

    def put(self, thread_id: str, state: ConversationState) -> None:
        """Lưu state cho thread_id (thay thế bản cũ nếu có)."""
        with self._lock:
            state.updated_at = time.time()
            self._store[thread_id] = state

    def evict_expired(self) -> int:
        now = time.time()
        with self._lock:
            expired = [
                k for k, v in self._store.items() if now - v.updated_at > self._ttl
            ]
            for k in expired:
                del self._store[k]
        return len(expired)


_store: ConversationStateStore | None = None
_store_lock = threading.Lock()


def get_conversation_store() -> ConversationStateStore:
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = ConversationStateStore()
    return _store
