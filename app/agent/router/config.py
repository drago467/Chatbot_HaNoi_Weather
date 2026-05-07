"""Router configuration — paths, thresholds, constants."""

import os
from pathlib import Path

# ── Ollama (primary inference backend) ──
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "hanoi-weather-router")

# ── Thresholds ──
# Default 0.74 = T4 floor (5-tier scheme). Reject only T5 (smalltalk/POI/OOD).
# Xem experiments/calibration/REPORT.md để hiểu rationale.
CONFIDENCE_THRESHOLD = float(os.getenv("SLM_CONFIDENCE_THRESHOLD", "0.74"))

# ── Per-intent thresholds ──
# v7.1 dùng 5-tier confidence (0.62/0.74/0.80/0.85/0.92). Phase 10 calibration
# analysis (experiments/calibration/REPORT.md) trên 385 val samples cho thấy:
#   - ECE overall 0.087 (moderate)
#   - T5 (0.62) underconfident +26pp; gồm 88% smalltalk/POI/OOD đúng semantic
#   - T4 (0.74) underconfident +12pp (acc 0.86); thrown across all intents
#   - Thresholds v6 cũ (0.73-0.85) reject 43% samples → fallback (lãng phí compute)
#   - Uniform τ=0.74: fast-path 91.4%, acc 89.8% (vs current 56.6%/93.1%)
# → adopt uniform 0.74 = T4 floor; reject chỉ T5 (smalltalk fallback safety).
PER_INTENT_THRESHOLDS: dict[str, float] = {
    "current_weather":      0.74,
    "hourly_forecast":      0.74,
    "daily_forecast":       0.74,
    "weather_overview":     0.74,
    "rain_query":           0.74,
    "temperature_query":    0.74,
    "wind_query":           0.74,
    "humidity_fog_query":   0.74,
    "historical_weather":   0.74,
    "location_comparison":  0.74,
    "activity_weather":     0.74,
    "expert_weather_param": 0.74,
    "weather_alert":        0.74,
    "seasonal_context":     0.74,
    "smalltalk_weather":    0.74,
}

# ── Feature flag ──
USE_SLM_ROUTER = os.getenv("USE_SLM_ROUTER", "false").lower() in ("true", "1", "yes")

# ── System prompt — Multi-turn ChatML routing + rewriting ──
# Prompt nội dung sống ở data/router/system_prompt.txt (cùng file push lên HF
# dataset repo) → load đúng nội dung đã train, không hardcode trong code.
# 4-keys JSON output: intent, scope, confidence, rewritten_query (null if N/A).
_PROMPT_PATH = (
    Path(__file__).resolve().parents[3] / "data/router/system_prompt.txt"
)
ROUTER_SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")

# ── Intents + Scopes (must match training data) ──
VALID_INTENTS = [
    "current_weather", "hourly_forecast", "daily_forecast", "weather_overview",
    "rain_query", "temperature_query", "wind_query", "humidity_fog_query",
    "historical_weather", "location_comparison", "activity_weather",
    "expert_weather_param", "weather_alert", "seasonal_context", "smalltalk_weather",
]
VALID_SCOPES = ["city", "district", "ward"]
