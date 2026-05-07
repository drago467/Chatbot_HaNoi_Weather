"""Router configuration — paths, thresholds, constants."""

import os
from pathlib import Path

# ── Ollama (primary inference backend) ──
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "hanoi-weather-router")

# ── Thresholds ──
CONFIDENCE_THRESHOLD = float(os.getenv("SLM_CONFIDENCE_THRESHOLD", "0.75"))

# ── Per-intent thresholds ──
# v7.1 dùng 5-tier confidence (0.62/0.74/0.80/0.85/0.92). Thresholds 0.73-0.85
# bên dưới giữ nguyên từ v6 — eval v7.1 đã đạt 89.6% routing acc với chính
# thresholds này nên không tune lại trong Phase 9. Calibration analysis (ECE)
# + threshold tuning theo distribution v7.1 defer Phase 10.
PER_INTENT_THRESHOLDS: dict[str, float] = {
    "current_weather":      0.82,
    "hourly_forecast":      0.82,
    "daily_forecast":       0.80,
    "weather_overview":     0.85,
    "rain_query":           0.85,
    "temperature_query":    0.82,
    "wind_query":           0.80,
    "humidity_fog_query":   0.82,
    "historical_weather":   0.82,
    "location_comparison":  0.82,
    "activity_weather":     0.75,
    "expert_weather_param": 0.79,
    "weather_alert":        0.73,
    "seasonal_context":     0.78,
    "smalltalk_weather":    0.85,
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
