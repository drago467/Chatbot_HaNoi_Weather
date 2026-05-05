"""Custom CSS loader for the HanoiAir Chatbot Streamlit UI.

CSS được tách sang `app/ui/static/styles.css` để dễ chỉnh sửa và xem diff.
Module này chỉ cung cấp `CUSTOM_CSS` (đã wrap trong `<style>` tag) như cũ —
giữ nguyên backward compat cho `app.py: from app.ui.styles import CUSTOM_CSS`.
"""

from pathlib import Path

_CSS_PATH = Path(__file__).parent / "static" / "styles.css"
_CSS_CONTENT = _CSS_PATH.read_text(encoding="utf-8")

CUSTOM_CSS = f"<style>\n{_CSS_CONTENT}\n</style>"
