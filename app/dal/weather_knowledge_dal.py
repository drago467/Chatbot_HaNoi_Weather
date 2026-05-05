"""Weather Knowledge DAL - Detect Hanoi-specific weather phenomena.

Mỗi hiện tượng (nồm ẩm, gió Lào, rét đậm, ...) có 1 detector riêng nhận dict
weather + month, trả `Optional[dict]` (phenomenon entry hoặc None nếu chưa
match điều kiện). `detect_hanoi_weather_phenomena` chỉ gọi tuần tự + filter
None — dễ test/giải thích từng hiện tượng độc lập.
"""

from typing import Any, Dict, List, Optional

from app.config.thresholds import KTTV_THRESHOLDS
from app.dal.timezone_utils import now_ict


# ── Single-phenomenon detectors ───────────────────────────────────────


def _detect_nom_am(month: int, *, humidity, temp, dew_point) -> Optional[Dict[str, Any]]:
    """Nồm ẩm (Spring Dampness) — chỉ Tháng 2-4."""
    if month not in (2, 3, 4) or humidity is None:
        return None
    dew_diff = temp - dew_point if temp is not None and dew_point is not None else 999
    if humidity >= KTTV_THRESHOLDS["NOM_AM_HUMIDITY"] and dew_diff <= 2:
        return {
            "type": "nom_am", "name": "Nồm ẩm", "severity": "high",
            # Description neutral (facts-only): mô tả vật lý ngưng tụ thay vì
            # advice cứng. Advice cụ thể là việc của LLM compose theo context.
            "description": (
                f"Nồm ẩm mức độ cao! Độ ẩm {humidity}%, nhiệt {temp}°C, "
                f"điểm sương {dew_point}°C - Hơi nước ngưng tụ trên bề mặt "
                f"mát do độ ẩm cao và chênh lệch nhiệt-điểm sương thấp."
            ),
        }
    if (humidity >= KTTV_THRESHOLDS["NOM_AM_HUMIDITY_MEDIUM"]
            and dew_diff <= KTTV_THRESHOLDS["NOM_AM_DEW_DIFF_MEDIUM"]):
        return {
            "type": "nom_am", "name": "Nồm ẩm", "severity": "medium",
            "description": f"Độ ẩm cao mức độ vừa ({humidity}%) - Cảm giác ẩm ướt",
        }
    return None


def _detect_gio_lao(month: int, *, wind_deg, wind_speed, humidity) -> Optional[Dict[str, Any]]:
    """Gió Lào (T5-8 + Tây Nam + humidity < 55%) hoặc Gió Tây mạnh (cùng hướng nhưng còn ẩm)."""
    if month not in (5, 6, 7, 8):
        return None
    if wind_deg is None or not (180 <= wind_deg <= 270) or wind_speed <= 5:
        return None
    if humidity is not None and humidity < 55:
        return {
            "type": "gio_lao", "name": "Gió Lào", "severity": "high",
            "description": (
                f"Gió Lào! Gió nóng từ Tây Nam, độ ẩm chỉ {humidity}% - "
                f"Trời oi nóng, không khí rất khô, cần uống nhiều nước"
            ),
        }
    return {
        "type": "gio_tay", "name": "Gió Tây", "severity": "medium",
        # Description neutral: chỉ giữ fact (cường độ gió). Advice là việc của LLM.
        "description": f"Gió Tây mạnh ({wind_speed} m/s).",
    }


def _detect_gio_dong_bac(month: int, *, wind_deg, wind_speed, temp) -> Optional[Dict[str, Any]]:
    """Gió mùa Đông Bắc — T10 đến T3 năm sau, gió Bắc/Đông Bắc."""
    if month not in (10, 11, 12, 1, 2, 3):
        return None
    if wind_deg is None or wind_speed <= 5:
        return None
    if not (wind_deg >= 315 or wind_deg <= 90):
        return None
    return {
        "type": "gio_dong_bac", "name": "Gió mùa Đông Bắc", "severity": "medium",
        "description": (
            f"Gió mùa Đông Bắc! Gió lạnh từ Đông Bắc, nhiệt có thể xuống "
            f"{temp}°C - Trời trở lạnh, cần mặc ấm"
        ),
    }


def _detect_ret_dam(month: int, *, temp, clouds) -> Optional[Dict[str, Any]]:
    """Rét đậm (T11-3, KTTV: Tavg ≤ 15°C + clouds ≥ 70%) hoặc Rét nhẹ (chỉ lạnh)."""
    if month not in (11, 12, 1, 2, 3) or temp is None:
        return None
    if temp >= KTTV_THRESHOLDS["RET_DAM"]:
        return None
    if clouds is not None and clouds >= 70:
        severity = "high" if temp < KTTV_THRESHOLDS["RET_HAI"] else "medium"
        return {
            "type": "ret_dam", "name": "Rét đậm", "severity": severity,
            "description": (
                f"Rét đậm! Nhiệt độ dưới {KTTV_THRESHOLDS['RET_DAM']}°C, "
                f"trời âm u - Cần mặc ấm, hạn chế ra ngoài"
            ),
        }
    return {
        "type": "ret_nhe", "name": "Rét", "severity": "low",
        "description": f"Nhiệt độ thấp ({temp}°C) - Cần mặc ấm nhẹ",
    }


def _detect_ret_nang_ban(month: int, *, temp, humidity) -> Optional[Dict[str, Any]]:
    """Rét nàng Bân — T3 đột ngột rét sau chuỗi ấm."""
    if month != 3 or temp is None or humidity is None:
        return None
    if temp >= 18 or humidity <= 80:
        return None
    return {
        "type": "ret_nang_ban", "name": "Rét nàng Bân", "severity": "medium",
        # Description neutral: sửa "ấm u" → "ấm áp"; bỏ "Thay đổi nhiệt độ đột ngột"
        # (redundant). Giữ "đặc trưng đợt rét cuối xuân" — classification của
        # hiện tượng (climate science), không phải advice.
        "description": (
            f"Rét nàng Bân! Nhiệt đột ngột xuống {temp}°C sau chuỗi "
            f"ngày ấm áp; đặc trưng đợt rét cuối xuân."
        ),
    }


def _detect_nang_nong(month: int, *, temp) -> Optional[Dict[str, Any]]:
    """Nắng nóng — T5-9 với cascade severity theo KTTV."""
    if month not in (5, 6, 7, 8, 9) or temp is None:
        return None
    if temp >= KTTV_THRESHOLDS["NANG_NONG_DB"]:
        severity = "high"
    elif temp >= KTTV_THRESHOLDS["NANG_NONG_GAY_GAT"]:
        severity = "medium"
    elif temp >= KTTV_THRESHOLDS["NANG_NONG"]:
        severity = "low"
    else:
        return None
    return {
        "type": "nang_nong", "name": "Nắng nóng", "severity": severity,
        "description": (
            f"Nắng nóng mức độ {severity}: {temp}°C - Hạn chế ra ngoài giờ trưa, "
            f"uống nhiều nước"
        ),
    }


def _detect_suong_mu(month: int, *, visibility, temp) -> Optional[Dict[str, Any]]:
    """Sương mù: dày (<200m) — luôn báo. Vừa — chỉ T1-2 hoặc T3 + temp <20."""
    if visibility is None:
        return None
    if visibility < 200:
        return {
            "type": "suong_mu", "name": "Sương mù dày", "severity": "high",
            # Description neutral: chỉ giữ fact tầm nhìn.
            "description": f"Sương mù rất dày, tầm nhìn dưới {visibility}m.",
        }
    if visibility >= KTTV_THRESHOLDS["SUONG_MU_VISIBILITY"]:
        return None
    seasonal = month in (1, 2) or (month == 3 and temp is not None and temp < 20)
    if not seasonal:
        return None
    return {
        "type": "suong_mu", "name": "Sương mù", "severity": "medium",
        "description": f"Sương mù! Tầm nhìn thấp ({visibility}m) - Cẩn thận khi lái xe",
    }


def _detect_mua_dong(month: int, *, weather_main) -> Optional[Dict[str, Any]]:
    """Mưa dông — T4-10 + weather_main = 'Thunderstorm'."""
    if month not in (4, 5, 6, 7, 8, 9, 10) or weather_main != "Thunderstorm":
        return None
    return {
        "type": "mua_dong", "name": "Mưa dông", "severity": "high",
        # Description neutral: giữ fact (dông + mưa + sét). Advice là việc của LLM.
        "description": "Mưa dông, có giông kèm mưa và khả năng sét.",
    }


def detect_hanoi_weather_phenomena(weather_data: Dict[str, Any]) -> Dict[str, Any]:
    """Detect 8 hiện tượng đặc thù Hà Nội theo KTTV + seasonal pattern.

    Args:
        weather_data: Weather dict (kèm `month` 1-12; mặc định now_ict().month).

    Returns:
        {"phenomena": list[dict], "has_dangerous": bool}
    """
    month = weather_data.get("month", now_ict().month)
    fields = {
        "humidity": weather_data.get("humidity"),
        "dew_point": weather_data.get("dew_point"),
        "temp": weather_data.get("temp"),
        "wind_deg": weather_data.get("wind_deg"),
        "wind_speed": weather_data.get("wind_speed", 0),
        "weather_main": weather_data.get("weather_main", ""),
        "visibility": weather_data.get("visibility"),
        "clouds": weather_data.get("clouds"),
    }

    detectors = (
        _detect_nom_am(month, humidity=fields["humidity"], temp=fields["temp"],
                       dew_point=fields["dew_point"]),
        _detect_gio_lao(month, wind_deg=fields["wind_deg"], wind_speed=fields["wind_speed"],
                        humidity=fields["humidity"]),
        _detect_gio_dong_bac(month, wind_deg=fields["wind_deg"], wind_speed=fields["wind_speed"],
                             temp=fields["temp"]),
        _detect_ret_dam(month, temp=fields["temp"], clouds=fields["clouds"]),
        _detect_ret_nang_ban(month, temp=fields["temp"], humidity=fields["humidity"]),
        _detect_nang_nong(month, temp=fields["temp"]),
        _detect_suong_mu(month, visibility=fields["visibility"], temp=fields["temp"]),
        _detect_mua_dong(month, weather_main=fields["weather_main"]),
    )
    phenomena: List[Dict[str, Any]] = [p for p in detectors if p is not None]
    return {
        "phenomena": phenomena,
        "has_dangerous": any(p.get("severity") == "high" for p in phenomena),
    }



def get_seasonal_average(month: int) -> Dict[str, Any]:
    """Get average weather for a specific month in Hanoi.
    
    Args:
        month: Month number (1-12)
        
    Returns:
        Dictionary with average weather data
    """
    seasonal_data = {
        1: {"temp_avg": 17, "temp_min": 14, "temp_max": 20, "humidity": 75, "rain_days": 6},
        2: {"temp_avg": 19, "temp_min": 15, "temp_max": 23, "humidity": 78, "rain_days": 8},
        3: {"temp_avg": 22, "temp_min": 18, "temp_max": 27, "humidity": 80, "rain_days": 12},
        4: {"temp_avg": 27, "temp_min": 22, "temp_max": 32, "humidity": 82, "rain_days": 15},
        5: {"temp_avg": 30, "temp_min": 25, "temp_max": 35, "humidity": 80, "rain_days": 18},
        6: {"temp_avg": 31, "temp_min": 26, "temp_max": 36, "humidity": 78, "rain_days": 16},
        7: {"temp_avg": 31, "temp_min": 26, "temp_max": 36, "humidity": 76, "rain_days": 14},
        8: {"temp_avg": 30, "temp_min": 26, "temp_max": 35, "humidity": 80, "rain_days": 17},
        9: {"temp_avg": 29, "temp_min": 24, "temp_max": 33, "humidity": 79, "rain_days": 14},
        10: {"temp_avg": 26, "temp_min": 21, "temp_max": 30, "humidity": 76, "rain_days": 10},
        11: {"temp_avg": 22, "temp_min": 18, "temp_max": 26, "humidity": 74, "rain_days": 7},
        12: {"temp_avg": 18, "temp_min": 14, "temp_max": 22, "humidity": 73, "rain_days": 5},
    }
    return seasonal_data.get(month, {"temp_avg": 25, "humidity": 75, "rain_days": 10})


def compare_with_seasonal(weather_data: Dict[str, Any], month: int = None) -> Dict[str, Any]:
    """Compare current weather with seasonal average.
    
    Args:
        weather_data: Current weather data
        month: Month (1-12). If not provided, uses current month.
        
    Returns:
        Dictionary with comparison results
    """
    from datetime import datetime
    if month is None:
        month = now_ict().month
    seasonal = get_seasonal_average(month)
    
    comparisons = []
    
    if weather_data.get("temp") is not None:
        diff = weather_data["temp"] - seasonal["temp_avg"]
        if diff > 3:
            comparisons.append(f"Nóng hơn bình thường {diff:.1f}°C")
        elif diff < -3:
            comparisons.append(f"Lạnh hơn bình thường {abs(diff):.1f}°C")
        else:
            comparisons.append("Nhiệt độ bình thường theo mùa")
    
    if weather_data.get("humidity") is not None:
        hum_diff = weather_data["humidity"] - seasonal["humidity"]
        if hum_diff > 10:
            comparisons.append("Độ ẩm cao hơn bình thường")
        elif hum_diff < -10:
            comparisons.append("Độ ẩm thấp hơn bình thường")
    
    # Validate month
    month_names = [
        "Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4", "Tháng 5", "Tháng 6",
        "Tháng 7", "Tháng 8", "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12"
    ]
    if month < 1 or month > 12:
        month_name = "Không xác định"
    else:
        month_name = month_names[month - 1]
    
    return {
        "seasonal_avg": seasonal,
        "comparisons": comparisons,
        "month_name": month_name
    }


def get_weather_summary_text(weather_data: Dict[str, Any]) -> str:
    """Generate a natural language weather summary in Vietnamese.
    
    Args:
        weather_data: Weather data dictionary
        
    Returns:
        Vietnamese weather summary
    """
    temp = weather_data.get("temp")
    humidity = weather_data.get("humidity")
    wind_speed = weather_data.get("wind_speed")
    wind_deg = weather_data.get("wind_deg")
    weather_main = weather_data.get("weather_main", "")
    
    from app.dal.weather_helpers import wind_deg_to_vietnamese
    
    parts = []
    
    # Temperature
    if temp is not None:
        if temp < 15:
            parts.append(f"nhiệt độ {temp}°C, lạnh")
        elif temp < 25:
            parts.append(f"nhiệt độ {temp}°C, mát lạnh")
        elif temp < 32:
            parts.append(f"nhiệt độ {temp}°C, thoải mái")
        else:
            parts.append(f"nhiệt độ {temp}°C, nóng")
    
    # Weather condition
    if weather_main:
        from app.config.thresholds import WEATHER_DESCRIPTIONS
        desc = WEATHER_DESCRIPTIONS.get(weather_main, weather_main)
        parts.append(desc)
    
    # Humidity
    if humidity is not None:
        from app.config.thresholds import KTTV_THRESHOLDS
        if humidity >= KTTV_THRESHOLDS.get("NOM_AM_HUMIDITY_MEDIUM", 85):
            parts.append(f"độ ẩm cao {humidity}%")
    
    # Wind
    if wind_speed is not None and wind_deg is not None:
        wind_dir = wind_deg_to_vietnamese(wind_deg)
        parts.append(f"gió {wind_dir} {wind_speed} m/s")
    
    return ", ".join(parts) if parts else "Không có dữ liệu"