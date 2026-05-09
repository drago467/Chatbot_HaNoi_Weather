"""FastAPI app entry point.

Khởi tạo app, middleware, logging, routes. Dùng lifespan thay cho on_event
(cách mới, tránh deprecation warning).

Run:
    uvicorn app.api.main:app --host 0.0.0.0 --port 8000
"""

import asyncio
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Single load_dotenv() cho process — phải gọi trước mọi `from app.*` để các
# module-level `os.getenv` (vd `app.agent.conversation_state._TTL_SECONDS`,
# `app.agent.router.config.OLLAMA_BASE_URL`) đọc đúng giá trị từ .env.
# Các entry point khác (experiments/, training/, scripts/) đã có load_dotenv riêng.
load_dotenv()

# Monkey-patch langchain trước khi import agent
from app.core import compat  # noqa: F401, E402
from app.core.logging_config import get_logger, setup_logging  # noqa: E402

setup_logging()
logger = get_logger(__name__)


# R18 fix P0-3 — ConversationStateStore background eviction.
# `evict_expired()` đã tồn tại trong app/agent/conversation_state.py:89 nhưng pre-R18
# KHÔNG có chỗ nào trong production gọi nó (chỉ test gọi). Hệ quả: dict thread_id →
# state grows unbounded suốt server uptime; TTL=3600s không tự dọn → memory leak.
# Background task chạy mỗi 5 phút, gọi method có sẵn (không phá API).
_EVICT_INTERVAL_SECONDS = int(os.getenv("CONVERSATION_EVICT_INTERVAL", "300"))


async def _conversation_evict_loop() -> None:
    """Periodic eviction. Idempotent — exception 1 lần không kill task."""
    from app.agent.conversation_state import get_conversation_store
    store = get_conversation_store()
    while True:
        try:
            await asyncio.sleep(_EVICT_INTERVAL_SECONDS)
            evicted = store.evict_expired()
            if evicted:
                logger.info("ConversationStateStore evicted %d expired entries", evicted)
        except asyncio.CancelledError:
            raise  # propagate shutdown signal
        except Exception as e:
            logger.warning("Eviction loop error (continuing): %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan: spawn evict task + log startup. Shutdown: cancel + cleanup."""
    logger.info("FastAPI starting up...")
    evict_task = asyncio.create_task(_conversation_evict_loop())
    try:
        yield
    finally:
        logger.info("FastAPI shutting down...")
        evict_task.cancel()
        try:
            await evict_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Chatbot Thời tiết Hà Nội API",
    description="API cho chatbot thời tiết Hà Nội với SLM router + multi-turn + 27 tools",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — scope cho phép tất cả, production thì tighten
_cors_origins = os.getenv("API_CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký routes
from app.api.routes import chat, conversations, health, jobs, weather  # noqa: E402

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(jobs.router)
app.include_router(weather.router)


@app.get("/")
def root():
    """Trả link tới Swagger UI."""
    return {
        "name": "Chatbot Thời tiết Hà Nội API",
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
    }
