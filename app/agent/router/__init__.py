"""SLM Intent Router — phân loại intent + scope, thu hẹp tool set."""

from app.agent.router.slm_router import SLMRouter, get_router
from app.agent.router.tool_mapper import get_focused_tools, PRIMARY_TOOL_MAP
from app.agent.router.config import ROUTER_CONFIG

__all__ = [
    "SLMRouter",
    "get_router",
    "get_focused_tools",
    "PRIMARY_TOOL_MAP",
    "ROUTER_CONFIG",
]
