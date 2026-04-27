"""Named constants thay cho magic numbers trong code.

Các giá trị Ở ĐÂY KHÔNG phải config tunable runtime — chúng là hằng số phản
ánh giới hạn API hoặc default thiết kế. Nếu cần env override → dùng
`app/config/settings.py`.

Khi thêm constant: đặt ở phần đúng nhóm + comment lý do (vì sao chính số này).

Chưa migrate trong PR1.2 (defer):
- SQL `INTERVAL '2 hours' / '30 minutes' / '24 hours'` ở DAL — đụng nhiều
  file (weather_dal, weather_aggregate_dal, alerts_dal) cần test DAL
  aggregate trước. Sẽ làm ở PR1.2b sau.
- `confidence_threshold = 0.75` default ở `slm_router.py:95` — đã có sẵn
  `CONFIDENCE_THRESHOLD` ở `app/agent/router/config.py:10` (đọc từ env).
  Sẽ thay default literal sang import constant ở PR1.2b.
"""

# ── Forecast horizon (giới hạn API OpenWeather) ─────────────────────────────
# Hourly forecast — OpenWeather One Call API trả tối đa 48 giờ.
FORECAST_MAX_HOURS: int = 48

# Daily forecast — OpenWeather One Call API trả tối đa 8 ngày.
FORECAST_MAX_DAYS: int = 8

# ── UV thresholds ───────────────────────────────────────────────────────────
# Default ngưỡng UV "an toàn" cho `get_uv_safe_windows`. UV >= 5 = trung bình
# theo WHO; UV < 5 cho phép hoạt động ngoài trời mà không cần che chắn.
UVI_SAFE_DEFAULT: float = 5.0
