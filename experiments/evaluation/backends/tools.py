"""Tool subset selector cho 6-config eval.

`tool_path='full_27'` → toàn bộ 27 LangChain tools (`app/agent/tools/__init__.py:TOOLS`).
`tool_path='router_prefilter'` → subset từ `PRIMARY_TOOL_MAP[intent][scope]`
(`app/agent/router/tool_mapper.py`); fallback full_27 nếu router không predict
intent (low confidence / NoneRouter / parse error).

Tool implementation production GIỮ NGUYÊN. Adapter chỉ select subset by reference.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_tool_subset(
    tool_path: str,
    intent: Optional[str] = None,
    scope: str = "city",
) -> list:
    """Return list LangChain BaseTool theo `tool_path`.

    Args:
        tool_path: "full_27" hoặc "router_prefilter".
        intent: Predicted intent từ router. None → fallback full_27.
        scope: "city" / "district" / "ward". Default "city" cho location_comparison.

    Returns:
        list of LangChain `BaseTool` instances. Order theo PRIMARY_TOOL_MAP.
    """
    from app.agent.tools import TOOLS

    if tool_path == "full_27":
        return list(TOOLS)

    if tool_path != "router_prefilter":
        raise ValueError(f"Unknown tool_path: {tool_path!r}")

    if not intent:
        logger.debug("router_prefilter: intent=None → fallback full_27")
        return list(TOOLS)

    from app.agent.router.tool_mapper import PRIMARY_TOOL_MAP

    scope_map = PRIMARY_TOOL_MAP.get(intent)
    if scope_map is None:
        logger.warning(
            "intent=%r not in PRIMARY_TOOL_MAP → fallback full_27", intent
        )
        return list(TOOLS)

    tools = scope_map.get(scope) or scope_map.get("city")
    if not tools:
        logger.warning(
            "PRIMARY_TOOL_MAP[%r][%r] empty → fallback full_27", intent, scope
        )
        return list(TOOLS)

    return list(tools)
