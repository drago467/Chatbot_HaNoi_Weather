"""Activity-specific weather profiles — research-backed thresholds.

R18 P1-9: Pre-R18 mọi activity dùng cùng threshold (`THRESHOLDS` generic +
`_ACTIVITY_SCORING` simple temp/pop/uvi/wind cap) → "nên đi chạy bộ" và "nên
đi chụp ảnh" trả lời giống nhau khi cùng weather. Research best-practice
(arxiv 2506.14641, ACSM, WHO, WMO/Beaufort) cho thấy mỗi activity có
threshold khác nhau; áp dụng generic gây lời khuyên kém chất lượng.

Sources (defendable cho thesis):
- ACSM Expert Consensus on Exertional Heat Illness (2023): WBGT zones,
  heat acclimation, exercise warnings.
  https://rrm.com/acsm-heat-guidelines/
- WHO UV Index Q&A: protection thresholds (UVI 3+ requires SPF, 8+ very high).
  https://www.who.int/news-room/questions-and-answers/item/radiation-the-ultraviolet-(uv)-index
- WMO/Beaufort Scale: wind speed bands (3=gentle, 5=fresh, 6=strong, 7=near gale).
  https://en.wikipedia.org/wiki/Beaufort_scale
- NOAA/NWS Lightning Safety: 30-30 rule (water + outdoor events stop).
  https://www.weather.gov/safety/lightning-sports
- ASHRAE-55 + Lin & Matzarakis (2008): tropical PET thermal comfort (HK/HN).
  https://link.springer.com/article/10.1007/s41748-019-00090-4
- CS Kites / Mackite: kite flying wind range (3-8 m/s sweet spot).
  https://cskites.com/blog/how-much-wind-to-fly-a-kite-best-speed-guide/
- PhotoPills Golden Hour: photography light quality.
  https://www.photopills.com/articles/mastering-golden-hour-blue-hour-magic-hours-and-twilights
- American Tent / TentSupply: outdoor event tent wind ratings.
  https://americantent.com/blogs/now-trending/how-much-wind-can-a-tent-withstand

THESIS NOTES:
1. Tropical PET upper bound 35.4°C (Lin & Matzarakis 2008) hơn ASHRAE-55
   indoor 26°C → biện minh ngưỡng nhiệt cao hơn so với chatbot Tây.
2. `cau_ca` pressure thresholds có literature yếu (Peterson 1972 single
   study; Active Angling NZ skeptical). Ghi rõ là "correlational with
   fronts, not direct causation".
3. `pop_warning` cụ thể (0.2/0.3/0.4/0.5) là engineering choice
   (events strict, walking tolerant) — không có authoritative source.

PROFILE SCHEMA (mọi key đều optional — evaluator skip nếu thiếu):
    temp_optimal: (lo, hi) °C
    temp_warning_high / temp_warning_low: WARNING threshold
    temp_danger_high: DANGER → khong_nen
    uvi_warning / uvi_danger: WHO UV index thresholds
    pop_warning / pop_danger: rain probability (0.0-1.0)
    wind_warning_high / wind_danger_high: m/s
    wind_optimal: (lo, hi) — chỉ cho activity cần gió (kite)
    wind_warning_low: m/s — kite không bay nếu < lo
    humidity_warning: high humidity (slows evap cooling for outdoor exercise)
    cloud_optimal: (lo, hi) — chỉ photography
    thunderstorm_danger: True nếu activity phải dừng khi giông
    source_notes: prose source citation
    hanoi_context: localized best-time-of-day note
"""

from __future__ import annotations

from typing import Any, Dict, Tuple


ACTIVITY_PROFILES: Dict[str, Dict[str, Any]] = {

    # ── 1. Chạy bộ ──
    "chay_bo": {
        "temp_optimal": (10, 20),
        "temp_warning_high": 28,        # ACSM WBGT > 28°C high heat-illness risk
        "temp_danger_high": 32,         # ACSM WBGT > 32°C cancel exercise
        "uvi_warning": 5,               # WHO 3+ requires protection, 6+ high
        "uvi_danger": 8,                # WHO 8-10 "very high"
        "humidity_warning": 80,         # AHA: high humidity slows evap cooling
        "wind_warning_high": 8,         # Beaufort 5 strong breeze, impedes pacing
        "pop_warning": 0.4,
        "thunderstorm_danger": True,
        "source_notes": (
            "ACSM Expert Consensus 2023; WHO UV Q&A; AHA warm-weather guidance"
        ),
        "hanoi_context": (
            "Tốt nhất sáng sớm 5-7h hoặc chiều tối 17-19h. Tránh 11-15h "
            "tháng May-Sep (WBGT >30°C + ẩm 80%+)"
        ),
    },

    # ── 2. Chụp ảnh ──
    "chup_anh": {
        "temp_optimal": (15, 30),       # comfort secondary, light primary
        "cloud_optimal": (30, 70),      # mây nhẹ-vừa cho ánh sáng đẹp
        "uvi_warning": 8,               # harsh contrast, not safety
        "pop_warning": 0.5,             # rain damages gear
        "wind_warning_high": 10,        # tripod stability
        "thunderstorm_danger": True,
        "source_notes": (
            "PhotoPills Golden Hour; landscape photography literature "
            "(30-70% cloud cover diffuses light optimally)"
        ),
        "hanoi_context": (
            "Golden hour Hanoi ~5h30-6h30 sáng và 17h-18h chiều. Mùa thu "
            "(Sep-Nov) là king season — clear skies + cirrus clouds"
        ),
    },

    # ── 3. Picnic ──
    "picnic": {
        "temp_optimal": (20, 28),
        "temp_warning_high": 32,        # group sedentary outdoor
        "temp_warning_low": 15,
        "pop_warning": 0.3,             # food + blankets — strict
        "wind_warning_high": 7,         # Beaufort 4 moderate, blows napkins/food
        "uvi_warning": 8,               # 2+ hr exposure
        "humidity_warning": 85,
        "thunderstorm_danger": True,
        "source_notes": (
            "ASHRAE-55 + tropical PET (Lin & Matzarakis 2008); Beaufort scale"
        ),
        "hanoi_context": (
            "Tốt nhất Mar-Apr và Oct-Nov (18-28°C, ít mưa). Tránh May-Sep "
            "(mưa rào bất ngờ). Tây Hồ / Bách Thảo sáng 8-10h hoặc chiều 15h30-17h30"
        ),
    },

    # ── 4. Đi dạo ──
    "di_dao": {
        "temp_optimal": (18, 30),       # broader comfort (low metabolic 2 MET)
        "temp_warning_high": 33,
        "temp_warning_low": 12,
        "uvi_warning": 8,
        "pop_warning": 0.5,             # umbrella sufficient
        "wind_warning_high": 11,        # Beaufort 6 strong breeze impedes walk
        "humidity_warning": 90,
        "thunderstorm_danger": True,
        "source_notes": (
            "ASHRAE-55 + tropical PET upper acceptability 35.4°C "
            "(Lin & Matzarakis 2008); WHO UV; Beaufort scale"
        ),
        "hanoi_context": (
            "Hồ Gươm / Old Quarter mùa thu (Oct-Nov, 22-28°C). Hè evenings "
            "18-21h sau hoàng hôn. Đông afternoons 14-16h khi nắng ấm"
        ),
    },

    # ── 5. Đua diều ──
    "dua_dieu": {
        "wind_optimal": (3, 7),         # CS Kites/Beaufort 3-4 ideal
        "wind_warning_low": 2,          # kites won't lift below Beaufort 2
        "wind_warning_high": 11,        # Beaufort 6 dangerous typical kites
        "wind_danger_high": 14,         # Beaufort 7 line snap / pull-down
        "temp_optimal": (15, 32),
        "pop_warning": 0.3,             # wet line + lightning
        "thunderstorm_danger": True,
        "source_notes": (
            "Beaufort scale (WMO); CS Kites & Mackite 4-10 mph single-line, "
            "up to 15 knots sport kites"
        ),
        "hanoi_context": (
            "Mùa thu (Sep-Nov) gió mùa đông bắc 3-6 m/s ideal. Bãi Sông Hồng / "
            "quảng trường Ba Đình. Tránh giông hè (gió giật >15 m/s)"
        ),
    },

    # ── 6. Câu cá ──
    "cau_ca": {
        "temp_optimal": (15, 30),
        "wind_warning_high": 8,         # Beaufort 5 line/casting control
        "pop_warning": 0.5,             # light rain OK; heavy unsafe
        "thunderstorm_danger": True,    # rod = lightning rod
        "uvi_warning": 9,
        "source_notes": (
            "Peterson (1972) trout pressure; Wired2Fish/InTheSpread "
            "synthesis (correlational with fronts, not direct causation — "
            "Active Angling NZ skeptical view)"
        ),
        "hanoi_context": (
            "Hồ Tây / Hồ Linh Đàm sáng sớm 5-8h (cá ăn mạnh, áp suất ổn). "
            "Trước cơn bão hè (áp giảm) cá ăn mạnh nhưng rút khi giông tới"
        ),
    },

    # ── 7. Bơi lội (outdoor) ──
    "boi_loi": {
        "temp_optimal": (26, 33),       # FINA pool 25-28°C, outdoor warmer OK
        "temp_warning_low": 22,         # cold-shock risk (RLSS)
        "wind_warning_high": 10,        # wind chill + chop
        "pop_warning": 0.3,             # rain itself OK; thunderstorm = stop
        "thunderstorm_danger": True,    # NOAA 30-30 — water deadly conductor
        "uvi_warning": 8,               # reflective water doubles UV
        "source_notes": (
            "NOAA/NWS Lightning Safety 30-30 rule; FINA water temp 25-28°C; "
            "cold-water shock literature (RLSS/Tipton)"
        ),
        "hanoi_context": (
            "Outdoor pools (Tây Hồ, Mỹ Đình) mở May-Sep. Sáng 6-9h hoặc "
            "chiều 16-18h tránh UV peak. Mùa giông KHỞI hành nếu nghe sấm 30s"
        ),
    },

    # ── 8. Sự kiện ngoài trời ──
    "su_kien": {
        "temp_optimal": (20, 30),
        "temp_warning_high": 33,
        "pop_warning": 0.2,             # 20% — strictest (tents + electronics + crowds)
        "pop_danger": 0.5,
        "wind_warning_high": 10,        # ~22 mph pop-up canopies fail
        "wind_danger_high": 16,         # ~36 mph engineered tent evac
        "thunderstorm_danger": True,
        "uvi_warning": 8,
        "source_notes": (
            "American Tent industry: evacuate sustained 35-38 mph (15.6-17 m/s); "
            "pop-up tents fail 20-30 mph (9-13 m/s); ACSM heat for crowd; NWS lightning"
        ),
        "hanoi_context": (
            "Festival season Oct-Apr (dry, gió mùa đông bắc đều). Tránh May-Sep "
            "(giông chiều 15-18h). Tents Mỹ Đình / Hoàng Thành neo chắc"
        ),
    },
}


# Generic fallback cho activities không có profile riêng
# (bike, tap_the_duc, phoi_do, du_lich, cam_trai, lam_vuon, leo_nui...).
# Conservative thresholds — tránh advise sai cho activity unknown.
GENERIC_ACTIVITY_PROFILE: Dict[str, Any] = {
    "temp_warning_high": 33,
    "temp_warning_low": 12,
    "uvi_warning": 8,
    "pop_warning": 0.5,
    "wind_warning_high": 12,
    "humidity_warning": 90,
    "thunderstorm_danger": True,
    "source_notes": "Generic fallback — conservative cap based on ASHRAE/WHO",
    "hanoi_context": "Hoạt động ngoài trời nói chung tốt nhất mùa thu (Oct-Nov)",
}


def get_profile(activity: str) -> Dict[str, Any]:
    """Resolve activity → profile (researched profile or GENERIC fallback)."""
    return ACTIVITY_PROFILES.get(activity, GENERIC_ACTIVITY_PROFILE)


# ─────────────────────────────────────────────────────────────────────
# Evaluator — produce issues / recommendations / severity
# ─────────────────────────────────────────────────────────────────────

# Severity escalation order
_SEV_RANK = {"ok": 0, "warning": 1, "danger": 2}


def _esc(current: str, new: str) -> str:
    """Return higher severity of (current, new)."""
    return new if _SEV_RANK[new] > _SEV_RANK[current] else current


def evaluate_activity(activity: str, weather: Dict[str, Any]) -> Dict[str, Any]:
    """Đánh giá weather vs activity profile.

    Args:
        activity: Activity key (chay_bo, chup_anh, ...)
        weather: dict với ít nhất `temp`, `humidity`, `pop`, `uvi`, `wind_speed`,
                 `weather_main` (canonical canonical keys sau dispatch.normalize_agg_keys)

    Returns:
        dict {
            "issues": [str, ...],          # vấn đề phát hiện
            "recommendations": [str, ...], # gợi ý hành động
            "severity": "ok"|"warning"|"danger",
            "profile_used": activity_key | "_generic_fallback",
            "source_notes": str,
            "hanoi_context": str,
        }
    """
    profile = get_profile(activity)
    is_generic = activity not in ACTIVITY_PROFILES

    issues: list[str] = []
    recs: list[str] = []
    severity = "ok"

    temp = weather.get("temp")
    humidity = weather.get("humidity")
    pop = weather.get("pop") or 0
    uvi = weather.get("uvi") or 0
    wind_speed = weather.get("wind_speed") or 0
    # Bug G fix: gió giật (gust) — peak gió ngắn hạn — là yếu tố nguy hiểm
    # cho mọi outdoor activity (lật ô, cây đổ, tốc bạt, dust event sport).
    # Dùng max(avg, gust) cho threshold danger/warning_high. wind_warning_low
    # (kite) vẫn dùng avg vì kite cần gió sustained, không phải gust.
    wind_gust = weather.get("wind_gust") or 0
    wind_effective = max(wind_speed, wind_gust)
    clouds = weather.get("clouds")
    weather_main = (weather.get("weather_main") or "").lower()

    # ── Temperature ──
    if temp is not None:
        if "temp_danger_high" in profile and temp >= profile["temp_danger_high"]:
            issues.append(f"Nhiệt {temp:.1f}°C — quá nóng cho {activity}")
            recs.append("KHÔNG NÊN — heat illness risk cao. Hoãn hoặc chọn khung mát hơn.")
            severity = _esc(severity, "danger")
        elif "temp_warning_high" in profile and temp >= profile["temp_warning_high"]:
            issues.append(f"Nhiệt {temp:.1f}°C cao")
            recs.append("Chọn sáng sớm (5-7h) hoặc chiều tối (17-19h); uống đủ nước.")
            severity = _esc(severity, "warning")
        if "temp_warning_low" in profile and temp <= profile["temp_warning_low"]:
            issues.append(f"Nhiệt {temp:.1f}°C thấp")
            recs.append("Mặc ấm, khởi động kỹ.")
            severity = _esc(severity, "warning")

    # ── UV ──
    if uvi >= profile.get("uvi_danger", 99):
        issues.append(f"UV {uvi:.1f} cực cao")
        recs.append("Tránh ra ngoài 10-14h; SPF50+ mandatory.")
        severity = _esc(severity, "danger")
    elif uvi >= profile.get("uvi_warning", 99):
        issues.append(f"UV {uvi:.1f} cao")
        recs.append("Đội mũ rộng vành, kem chống nắng SPF30+.")
        severity = _esc(severity, "warning")

    # ── Rain probability ──
    if pop >= profile.get("pop_danger", 99):
        issues.append(f"Xác suất mưa rất cao ({pop*100:.0f}%)")
        recs.append("KHÔNG NÊN — hoãn hoạt động.")
        severity = _esc(severity, "danger")
    elif pop >= profile.get("pop_warning", 99):
        issues.append(f"Có thể mưa ({pop*100:.0f}%)")
        recs.append("Mang áo mưa/ô; cân nhắc kế hoạch backup.")
        severity = _esc(severity, "warning")

    # ── Wind (3 cases: too low cho kite, too high cho chung, danger cho event) ──
    wind_lo = profile.get("wind_warning_low")
    if wind_lo is not None and wind_speed < wind_lo:
        issues.append(f"Gió yếu ({wind_speed:.1f} m/s)")
        recs.append("Diều khó bay; chờ gió ổn định 3-7 m/s.")
        severity = _esc(severity, "warning")

    wind_optimal = profile.get("wind_optimal")  # tuple (lo, hi)
    if wind_optimal is not None:
        lo, hi = wind_optimal
        if lo <= wind_speed <= hi:
            pass  # gió ideal, không issue
        # else: high case xử lý ở wind_warning_high bên dưới

    if wind_effective >= profile.get("wind_danger_high", 99):
        gust_note = f" (giật {wind_gust:.1f})" if wind_gust > wind_speed else ""
        issues.append(f"Gió rất mạnh {wind_effective:.1f} m/s{gust_note}")
        recs.append("NGUY HIỂM — không nên ra ngoài; tents có thể đổ.")
        severity = _esc(severity, "danger")
    elif wind_effective >= profile.get("wind_warning_high", 99):
        gust_note = f" (giật {wind_gust:.1f})" if wind_gust > wind_speed else ""
        issues.append(f"Gió mạnh {wind_effective:.1f} m/s{gust_note}")
        recs.append("Cẩn thận; cố định đồ đạc.")
        severity = _esc(severity, "warning")

    # ── Humidity ──
    if humidity is not None and humidity >= profile.get("humidity_warning", 999):
        issues.append(f"Ẩm cao ({humidity}%)")
        recs.append("Slow evaporative cooling — nghỉ thường xuyên, uống nước.")
        severity = _esc(severity, "warning")

    # ── Cloud (chỉ photography) ──
    if clouds is not None and "cloud_optimal" in profile:
        lo, hi = profile["cloud_optimal"]
        if clouds < lo:
            issues.append(f"Mây quá ít ({clouds}%) — ánh sáng gắt, bóng cứng")
            recs.append("Ưu tiên golden hour (sáng sớm/chiều tối).")
            severity = _esc(severity, "warning")
        elif clouds > hi:
            issues.append(f"Mây quá dày ({clouds}%) — ánh sáng phẳng")
            recs.append("Photo flat color; cân nhắc dời lịch.")
            severity = _esc(severity, "warning")

    # ── Thunderstorm — luôn danger ──
    if profile.get("thunderstorm_danger") and weather_main == "thunderstorm":
        issues.append("Đang giông sét")
        recs.append("DỪNG NGAY — vào nơi trú ẩn (NOAA 30-30 rule).")
        severity = _esc(severity, "danger")

    return {
        "issues": issues,
        "recommendations": recs,
        "severity": severity,
        "profile_used": activity if not is_generic else "_generic_fallback",
        "source_notes": profile.get("source_notes", ""),
        "hanoi_context": profile.get("hanoi_context", ""),
    }
