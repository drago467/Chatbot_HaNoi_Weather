"""Extract numeric values from flat VN output strings.

Sau R6, tool output có shape:
  {"nhiệt độ": "Ấm dễ chịu 25.7°C", "xác suất mưa": "Cao 83%", ...}

Eval/audit scripts cần trích số từ chuỗi combined "<nhãn> <số> <đơn vị>".
Module này cung cấp regex helpers tái sử dụng.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Optional, Tuple

_NUM_RE = re.compile(r"(-?\d+(?:[\.,]\d+)?)")


def extract_first_number(s: Any) -> Optional[float]:
    """Trích số đầu tiên trong chuỗi → float.

    'Ấm dễ chịu 25.7°C' → 25.7
    'Cao 83%'           → 83.0
    'Gió vừa cấp 4 (5.5 m/s), giật 9.4 m/s' → 4.0 (số đầu tiên, là cấp)

    Với các value cần extract số khác 'đầu tiên', dùng extract_all_numbers hoặc
    parse trực tiếp bằng regex phù hợp.
    """
    if not isinstance(s, str):
        if isinstance(s, (int, float)):
            return float(s)
        return None
    m = _NUM_RE.search(s)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except ValueError:
        return None


def extract_all_numbers(s: Any) -> list[float]:
    """Trích TẤT CẢ số trong chuỗi, giữ thứ tự xuất hiện.

    'Gió vừa cấp 4 (5.5 m/s), giật 9.4 m/s' → [4.0, 5.5, 9.4]
    """
    if not isinstance(s, str):
        return []
    nums: list[float] = []
    for m in _NUM_RE.finditer(s):
        try:
            nums.append(float(m.group(1).replace(",", ".")))
        except ValueError:
            continue
    return nums


def extract_labeled_value(d: Mapping[str, Any], key: str) -> Tuple[str, Optional[float]]:
    """d['nhiệt độ']='Ấm dễ chịu 25.7°C' → ('Ấm dễ chịu', 25.7).

    Args:
        d: flat VN dict
        key: VN key to look up

    Returns:
        (label_text, numeric_value). `label_text` is the string with numbers
        and common units stripped; either element can be empty/None if missing.
    """
    val = d.get(key)
    if val is None:
        return "", None
    if not isinstance(val, str):
        # Already numeric or structured
        num = float(val) if isinstance(val, (int, float)) else None
        return "", num
    num = extract_first_number(val)
    # Strip numbers + common units to get label prefix
    label = _NUM_RE.sub("", val)
    label = re.sub(r"[°C%hPam/sr\s\-\(\),\.]+$", "", label).strip()
    return label, num


def extract_wind_components(wind_str: Any) -> dict:
    """'Gió vừa cấp 4 (5.5 m/s), giật 9.4 m/s, hướng Nam' →
    {'beaufort': 4, 'avg_ms': 5.5, 'gust_ms': 9.4, 'direction': 'Nam'}.

    Phù hợp cho audit wind trong current/hourly builders.
    """
    result: dict = {"beaufort": None, "avg_ms": None, "gust_ms": None, "direction": None}
    if not isinstance(wind_str, str):
        return result
    # Beaufort: "cấp N"
    m = re.search(r"cấp\s+(\d+)", wind_str)
    if m:
        result["beaufort"] = int(m.group(1))
    # Avg: first "(N.N m/s)" — mặc định số m/s đầu tiên
    m = re.search(r"\((\d+(?:\.\d+)?)\s*m/s\)", wind_str)
    if m:
        result["avg_ms"] = float(m.group(1))
    # Gust: "giật N.N m/s"
    m = re.search(r"giật\s+(\d+(?:\.\d+)?)\s*m/s", wind_str)
    if m:
        result["gust_ms"] = float(m.group(1))
    # Direction: "hướng X"
    m = re.search(r"hướng\s+(\S+)", wind_str)
    if m:
        result["direction"] = m.group(1).rstrip(",.")
    return result


def extract_percentage(s: Any) -> Optional[int]:
    """'Cao 83%' → 83. Return int for cleaner comparisons."""
    if not isinstance(s, str):
        return None
    m = re.search(r"(\d+)\s*%", s)
    if m:
        return int(m.group(1))
    return None
