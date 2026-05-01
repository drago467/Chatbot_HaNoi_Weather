"""Pin file extraction của BASE_PROMPT_TEMPLATE.

PR1.4 đã move text BASE_PROMPT_TEMPLATE từ Python literal trong agent.py
sang `app/agent/prompts/base_prompt.vi.txt`. Test này pin:
- File tồn tại + load thành công.
- Nội dung load không bị mất ký tự / rỗng.
- Format placeholders ({today_date} v.v.) còn nguyên — `.format(...)` work.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.agent.agent import BASE_PROMPT_TEMPLATE


_PROMPT_FILE = (
    Path(__file__).resolve().parent.parent.parent
    / "app" / "agent" / "prompts" / "base_prompt.vi.md"
)


def test_prompt_file_exists():
    assert _PROMPT_FILE.exists(), f"Missing: {_PROMPT_FILE}"


def test_prompt_loaded_non_empty():
    assert len(BASE_PROMPT_TEMPLATE) > 1000  # ~20K thực tế, sanity check


def test_prompt_starts_correctly():
    # File KHONG bat dau voi leading newline (continuation behavior).
    assert BASE_PROMPT_TEMPLATE.startswith("Bạn là trợ lý thời tiết Hà Nội")


def test_prompt_ends_with_newline():
    # File ends voi \n (triple-quoted string convention).
    assert BASE_PROMPT_TEMPLATE.endswith("\n")


def test_prompt_has_six_block_markers():
    """Pin: 6 block headers `## [1]` … `## [6]` đều còn (cấu trúc R11)."""
    for marker in (
        "## [1] SCOPE",
        "## [2] RUNTIME CONTEXT",
        "## [3] POLICY",
        "## [4] ROUTER",
        "## [5] RENDERER",
        "## [6] FALLBACK",
    ):
        assert marker in BASE_PROMPT_TEMPLATE, f"Missing block: {marker}"


def test_prompt_format_placeholders_intact():
    """Critical: placeholders dùng `.format(...)` phải còn — nếu mất, runtime
    sẽ KeyError khi inject runtime context.
    """
    required = (
        "{today_weekday}", "{today_date}", "{today_time}",
        "{yesterday_weekday}", "{yesterday_date}", "{yesterday_iso}",
        "{tomorrow_weekday}", "{tomorrow_date}", "{tomorrow_iso}",
        "{this_saturday_display}", "{this_sunday_display}",
        "{this_saturday}", "{this_sunday}",
        "{prev_week_table}", "{week_table}", "{next_week_table}",
        "{today_iso}",
    )
    for ph in required:
        assert ph in BASE_PROMPT_TEMPLATE, f"Missing placeholder: {ph}"


def test_prompt_format_smoke():
    """`.format(...)` với dummy values phải work (không có placeholder rơi rớt
    hoặc broken brace)."""
    dummy = {
        "today_weekday": "Thứ Hai", "today_date": "01/01", "today_time": "12:00",
        "yesterday_weekday": "Chủ Nhật", "yesterday_date": "31/12",
        "yesterday_iso": "2025-12-31",
        "tomorrow_weekday": "Thứ Ba", "tomorrow_date": "02/01",
        "tomorrow_iso": "2026-01-02",
        "this_saturday_display": "06/01", "this_sunday_display": "07/01",
        "this_saturday": "2026-01-06", "this_sunday": "2026-01-07",
        "prev_week_table": "Thứ Hai/T2/Mon: 25/12",
        "week_table": "Thứ Hai/T2/Mon: 01/01",
        "next_week_table": "Thứ Hai/T2/Mon: 08/01",
        "today_iso": "2026-01-01",
    }
    rendered = BASE_PROMPT_TEMPLATE.format(**dummy)
    assert "Thứ Hai" in rendered
    assert "01/01" in rendered
    # Không còn `{...}` placeholder chưa thay (bracket khác trong literal nội dung
    # text chỉ có trong markdown table, không phải format placeholder).
    # Để tránh false-positive, chỉ check các placeholder cụ thể đã thay:
    for ph_name in dummy:
        assert "{" + ph_name + "}" not in rendered


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
