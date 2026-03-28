"""Generate multi-task training data for SLM Router (Module 1b).

Extends existing routing data with contextual rewriting examples.
The model learns to:
1. Classify intent + scope (same as before) — from existing data
2. Optionally rewrite ambiguous queries when context is available

Output format (JSONL):
    {"input": "Còn ngày mai?",
     "context": {"location": "Cầu Giấy", "intent": "current_weather", "turn": 1},
     "output": {"intent": "daily_forecast", "scope": "district", "confidence": 0.91,
                "rewritten_query": "Dự báo thời tiết ngày mai ở quận Cầu Giấy?"}}

    {"input": "Thời tiết Cầu Giấy hiện tại?",
     "context": null,
     "output": {"intent": "current_weather", "scope": "district", "confidence": 0.95}}

Usage:
    python scripts/router/generate_rewrite_data.py
    python scripts/router/generate_rewrite_data.py --output data/router/rewrite_train.jsonl
    python scripts/router/generate_rewrite_data.py --use-llm  # Use GPT-4o-mini for variations
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
load_dotenv()

# ── Seed conversation templates ──
# Each template: (turn0_query, context_snippet, follow_up_queries)
# follow_up_queries: list of (ambiguous_query, rewritten_query, intent, scope)

_SEED_TEMPLATES = [
    # ─────────────── Pattern: Location carry-over ───────────────
    {
        "location": "Cầu Giấy", "location_scope": "district",
        "turn0": "Thời tiết Cầu Giấy hiện tại thế nào?",
        "turn0_intent": "current_weather",
        "followups": [
            ("Còn ngày mai?", "Dự báo thời tiết ngày mai ở quận Cầu Giấy như thế nào?", "daily_forecast", "district"),
            ("Tối mai có mưa không?", "Tối mai ở quận Cầu Giấy có mưa không?", "rain_query", "district"),
            ("Cuối tuần thế nào?", "Dự báo thời tiết cuối tuần ở quận Cầu Giấy?", "daily_forecast", "district"),
            ("Gió mạnh không?", "Gió ở quận Cầu Giấy hiện tại mạnh không?", "wind_query", "district"),
            ("Nhiệt độ bao nhiêu?", "Nhiệt độ hiện tại ở quận Cầu Giấy bao nhiêu độ?", "temperature_query", "district"),
        ],
    },
    {
        "location": "Đống Đa", "location_scope": "district",
        "turn0": "Quận Đống Đa hôm nay có mưa không?",
        "turn0_intent": "rain_query",
        "followups": [
            ("Mưa đến mấy giờ?", "Mưa ở quận Đống Đa đến mấy giờ thì tạnh?", "rain_query", "district"),
            ("Gió thế nào?", "Gió ở quận Đống Đa như thế nào?", "wind_query", "district"),
            ("Ngày mai trời quang không?", "Ngày mai ở quận Đống Đa trời có quang không?", "daily_forecast", "district"),
            ("Thế còn nhiệt độ?", "Nhiệt độ hiện tại ở quận Đống Đa bao nhiêu?", "temperature_query", "district"),
        ],
    },
    {
        "location": "Hoàn Kiếm", "location_scope": "district",
        "turn0": "Hoàn Kiếm nhiệt độ bao nhiêu?",
        "turn0_intent": "temperature_query",
        "followups": [
            ("Tối nay mấy độ?", "Tối nay quận Hoàn Kiếm nhiệt độ bao nhiêu?", "hourly_forecast", "district"),
            ("Ngày mai thế nào?", "Ngày mai ở quận Hoàn Kiếm thời tiết thế nào?", "daily_forecast", "district"),
            ("Dễ chịu không?", "Thời tiết quận Hoàn Kiếm hiện tại có dễ chịu không?", "activity_weather", "district"),
            ("Mặc gì đi?", "Ở quận Hoàn Kiếm hôm nay nên mặc gì khi ra ngoài?", "smalltalk_weather", "district"),
        ],
    },
    {
        "location": "Ba Đình", "location_scope": "district",
        "turn0": "Ba Đình hôm nay tổng quan thời tiết?",
        "turn0_intent": "weather_overview",
        "followups": [
            ("Ngày mai thế nào?", "Thời tiết ngày mai ở quận Ba Đình như thế nào?", "daily_forecast", "district"),
            ("Vậy còn cuối tuần?", "Cuối tuần này ở quận Ba Đình thời tiết ra sao?", "daily_forecast", "district"),
            ("Ở đó có mưa không?", "Quận Ba Đình hôm nay có mưa không?", "rain_query", "district"),
            ("Nơi đó gió thế nào?", "Gió ở quận Ba Đình hiện tại mạnh không?", "wind_query", "district"),
        ],
    },
    {
        "location": "Tây Hồ", "location_scope": "district",
        "turn0": "Chiều nay Tây Hồ mưa không?",
        "turn0_intent": "rain_query",
        "followups": [
            ("Tối nay thế nào?", "Tối nay ở quận Tây Hồ thời tiết ra sao?", "hourly_forecast", "district"),
            ("Ở đó sáng mai thế nào?", "Sáng mai ở quận Tây Hồ trời thế nào?", "hourly_forecast", "district"),
            ("Thế còn gió?", "Gió ở quận Tây Hồ chiều nay mạnh không?", "wind_query", "district"),
            ("Mưa đến mấy giờ tạnh?", "Mưa ở quận Tây Hồ đến mấy giờ thì tạnh?", "rain_query", "district"),
        ],
    },
    {
        "location": "Thanh Xuân", "location_scope": "district",
        "turn0": "Thanh Xuân hiện tại thế nào?",
        "turn0_intent": "current_weather",
        "followups": [
            ("Khu đó UV cao không?", "UV ở quận Thanh Xuân hiện tại có cao không?", "expert_weather_param", "district"),
            ("Thế còn gió mạnh không?", "Gió ở quận Thanh Xuân hiện tại có mạnh không?", "wind_query", "district"),
            ("Có nồm không?", "Quận Thanh Xuân có nồm ẩm không?", "humidity_fog_query", "district"),
            ("Ngày mai dự báo sao?", "Dự báo thời tiết ngày mai ở quận Thanh Xuân?", "daily_forecast", "district"),
        ],
    },
    {
        "location": "Hoàng Mai", "location_scope": "district",
        "turn0": "3 ngày tới Hoàng Mai thế nào?",
        "turn0_intent": "daily_forecast",
        "followups": [
            ("Ngày mai cụ thể?", "Ngày mai ở quận Hoàng Mai thời tiết cụ thể thế nào?", "weather_overview", "district"),
            ("Sáng mai mấy độ?", "Sáng mai ở quận Hoàng Mai nhiệt độ bao nhiêu?", "hourly_forecast", "district"),
            ("Có mưa không?", "Trong 3 ngày tới ở quận Hoàng Mai có mưa không?", "rain_query", "district"),
        ],
    },
    # ─────────────── Pattern: City-level carry-over ───────────────
    {
        "location": "Hà Nội", "location_scope": "city",
        "turn0": "Hà Nội hôm nay tổng quan?",
        "turn0_intent": "weather_overview",
        "followups": [
            ("Ngày mai thế nào?", "Hà Nội ngày mai thời tiết như thế nào?", "daily_forecast", "city"),
            ("Mưa không?", "Hà Nội hôm nay có mưa không?", "rain_query", "city"),
            ("Quận nào nóng nhất?", "Hà Nội hôm nay quận nào nóng nhất?", "location_comparison", "city"),
            ("Cuối tuần trời đẹp không?", "Cuối tuần này Hà Nội thời tiết có đẹp không?", "daily_forecast", "city"),
        ],
    },
    {
        "location": "Hà Nội", "location_scope": "city",
        "turn0": "Tuần này Hà Nội dự báo thế nào?",
        "turn0_intent": "daily_forecast",
        "followups": [
            ("Nhiệt độ xu hướng?", "Nhiệt độ Hà Nội tuần này có xu hướng như thế nào?", "temperature_query", "city"),
            ("Mưa nhiều không?", "Tuần này Hà Nội mưa nhiều không?", "rain_query", "city"),
            ("Nóng hơn bình thường không?", "Hà Nội tuần này nóng hơn bình thường không?", "seasonal_context", "city"),
        ],
    },
    # ─────────────── Pattern: Time shift ───────────────
    {
        "location": "Cầu Giấy", "location_scope": "district",
        "turn0": "Cầu Giấy bây giờ thế nào?",
        "turn0_intent": "current_weather",
        "followups": [
            ("Tối nay?", "Tối nay ở quận Cầu Giấy thời tiết ra sao?", "hourly_forecast", "district"),
            ("Sáng mai?", "Sáng mai ở quận Cầu Giấy nhiệt độ bao nhiêu?", "hourly_forecast", "district"),
            ("Ngày mai?", "Ngày mai ở quận Cầu Giấy dự báo thế nào?", "daily_forecast", "district"),
            ("Cuối tuần?", "Cuối tuần này ở quận Cầu Giấy thời tiết ra sao?", "daily_forecast", "district"),
        ],
    },
    # ─────────────── Pattern: Ward-level ───────────────
    {
        "location": "Dịch Vọng Hậu", "location_scope": "ward",
        "turn0": "Phường Dịch Vọng Hậu thời tiết hiện tại?",
        "turn0_intent": "current_weather",
        "followups": [
            ("UV cao không?", "UV ở phường Dịch Vọng Hậu hiện tại có cao không?", "expert_weather_param", "ward"),
            ("Tốt nhất đi bộ lúc mấy giờ?", "Ở phường Dịch Vọng Hậu lúc mấy giờ tốt nhất để đi bộ?", "activity_weather", "ward"),
            ("Ngày mai thế nào?", "Ngày mai ở phường Dịch Vọng Hậu thời tiết thế nào?", "daily_forecast", "ward"),
        ],
    },
    # ─────────────── Pattern: Activity + context ───────────────
    {
        "location": "Long Biên", "location_scope": "district",
        "turn0": "Long Biên hôm nay thế nào?",
        "turn0_intent": "weather_overview",
        "followups": [
            ("Phù hợp chạy bộ không?", "Ở quận Long Biên hôm nay có phù hợp để đi chạy bộ không?", "activity_weather", "district"),
            ("Lúc mấy giờ tốt nhất?", "Ở quận Long Biên hôm nay lúc mấy giờ là tốt nhất để chạy bộ?", "activity_weather", "district"),
            ("Ở đó ngày mai có mưa không?", "Ngày mai ở quận Long Biên có mưa không?", "rain_query", "district"),
        ],
    },
    # ─────────────── Anaphora patterns ───────────────
    {
        "location": "Hoàn Kiếm", "location_scope": "district",
        "turn0": "Hoàn Kiếm bây giờ mưa không?",
        "turn0_intent": "rain_query",
        "followups": [
            ("Ở đó mưa đến bao giờ?", "Ở quận Hoàn Kiếm mưa đến bao giờ thì tạnh?", "rain_query", "district"),
            ("Rồi sao gió thế nào?", "Gió ở quận Hoàn Kiếm sau khi tạnh mưa thế nào?", "wind_query", "district"),
            ("Chỗ đó tối nay có mưa không?", "Tối nay ở quận Hoàn Kiếm có mưa không?", "hourly_forecast", "district"),
            ("Khu đó UV bao nhiêu?", "UV ở quận Hoàn Kiếm hôm nay bao nhiêu?", "expert_weather_param", "district"),
        ],
    },
    {
        "location": "Đống Đa", "location_scope": "district",
        "turn0": "Đống Đa nhiệt độ bây giờ?",
        "turn0_intent": "temperature_query",
        "followups": [
            ("Chỗ đó có nồm không?", "Quận Đống Đa có nồm ẩm không?", "humidity_fog_query", "district"),
            ("Thế còn áp suất?", "Áp suất ở quận Đống Đa đang thay đổi không?", "expert_weather_param", "district"),
            ("Nơi đó ngày mai thế nào?", "Ngày mai ở quận Đống Đa thời tiết thế nào?", "daily_forecast", "district"),
            ("Vậy còn cuối tuần?", "Cuối tuần này ở quận Đống Đa thời tiết ra sao?", "daily_forecast", "district"),
        ],
    },
]

# ── Confidence values for synthetic data (realistic distribution) ──
_CONFIDENCE_VALUES = [0.88, 0.91, 0.93, 0.95, 0.87, 0.92, 0.89, 0.94, 0.96, 0.90]


def generate_routing_examples(existing_path: str) -> list[dict]:
    """Load existing routing data and wrap in multi-task format (context=null).

    Existing format: {"input": "...", "output": {"intent": ..., "scope": ..., "confidence": ...}}
    New format adds: "context": null (turn 1, no rewrite needed)
    """
    examples = []
    path = Path(existing_path)
    if not path.exists():
        print(f"Warning: {existing_path} not found, skipping")
        return examples

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                # Add context=null to existing examples
                if "context" not in rec:
                    rec["context"] = None
                examples.append(rec)
            except Exception:
                continue

    print(f"Loaded {len(examples)} routing examples from {existing_path}")
    return examples


def generate_rewrite_examples() -> list[dict]:
    """Generate contextual rewriting examples from seed templates."""
    examples = []

    for template in _SEED_TEMPLATES:
        location = template["location"]
        scope = template["location_scope"]
        turn0_intent = template["turn0_intent"]

        context = {
            "location": location,
            "intent": turn0_intent,
            "turn": 1,
        }

        for ambiguous, rewritten, intent, followup_scope in template["followups"]:
            conf = random.choice(_CONFIDENCE_VALUES)
            examples.append({
                "input": ambiguous,
                "context": context,
                "output": {
                    "intent": intent,
                    "scope": followup_scope,
                    "confidence": conf,
                    "rewritten_query": rewritten,
                },
            })

            # Also add a 3rd-turn example where context intent changes
            context_turn2 = {
                "location": location,
                "intent": intent,
                "turn": 2,
            }
            # Generate a self-referential follow-up for turn 3
            if intent in ("daily_forecast", "rain_query", "temperature_query"):
                if intent == "daily_forecast":
                    turn3_q = "Ngày kia thì sao?"
                    turn3_rw = f"Dự báo thời tiết ngày kia ở {'quận' if 'district' in followup_scope else 'phường'} {location}?"
                    turn3_intent = "daily_forecast"
                elif intent == "rain_query":
                    turn3_q = "Còn ngày mai?"
                    turn3_rw = f"Ngày mai ở {'quận' if 'district' in followup_scope else 'phường'} {location} có mưa không?"
                    turn3_intent = "rain_query"
                else:
                    turn3_q = "Chiều nay mấy độ?"
                    turn3_rw = f"Chiều nay ở {'quận' if 'district' in followup_scope else 'phường'} {location} nhiệt độ bao nhiêu?"
                    turn3_intent = "temperature_query"

                examples.append({
                    "input": turn3_q,
                    "context": context_turn2,
                    "output": {
                        "intent": turn3_intent,
                        "scope": followup_scope,
                        "confidence": random.choice(_CONFIDENCE_VALUES),
                        "rewritten_query": turn3_rw,
                    },
                })

    print(f"Generated {len(examples)} rewrite examples from {len(_SEED_TEMPLATES)} seed templates")
    return examples


def generate_no_rewrite_examples() -> list[dict]:
    """Generate examples where context is available BUT query is already self-contained.

    Model should NOT produce rewritten_query in these cases.
    """
    examples = []

    standalone_queries = [
        ("Quận Cầu Giấy hôm nay thế nào?", "weather_overview", "district", 0.93),
        ("Đống Đa ngày mai có mưa không?", "rain_query", "district", 0.91),
        ("Hoàn Kiếm nhiệt độ hiện tại?", "temperature_query", "district", 0.94),
        ("Ba Đình tuần này thế nào?", "daily_forecast", "district", 0.88),
        ("Tây Hồ chiều nay mưa không?", "rain_query", "district", 0.92),
        ("Hà Nội hôm nay tổng quan?", "weather_overview", "city", 0.96),
        ("Thanh Xuân ngày mai dự báo?", "daily_forecast", "district", 0.89),
        ("Long Biên bây giờ nhiệt độ?", "temperature_query", "district", 0.91),
        ("Bắc Từ Liêm cuối tuần có mưa không?", "rain_query", "district", 0.88),
        ("Phường Dịch Vọng thời tiết hiện tại?", "current_weather", "ward", 0.93),
    ]

    prev_contexts = [
        {"location": "Cầu Giấy", "intent": "current_weather", "turn": 1},
        {"location": "Hoàn Kiếm", "intent": "rain_query", "turn": 2},
        {"location": "Hà Nội", "intent": "weather_overview", "turn": 1},
    ]

    for query, intent, scope, conf in standalone_queries:
        ctx = random.choice(prev_contexts)
        examples.append({
            "input": query,
            "context": ctx,
            "output": {
                "intent": intent,
                "scope": scope,
                "confidence": conf,
                # No rewritten_query — query is already standalone
            },
        })

    print(f"Generated {len(examples)} no-rewrite examples (standalone queries with context)")
    return examples


def augment_with_llm(examples: list[dict], n_augments: int = 200) -> list[dict]:
    """Optional: Use GPT-4o-mini to generate additional variations.

    Samples n_augments examples and asks LLM to rephrase while preserving intent.
    """
    try:
        from openai import OpenAI
        client = OpenAI(base_url=os.getenv("API_BASE"), api_key=os.getenv("API_KEY"))
    except Exception as e:
        print(f"LLM augmentation skipped: {e}")
        return []

    augmented = []
    samples = random.sample(examples, min(n_augments, len(examples)))

    REPHRASE_PROMPT = """Bạn là người dùng chatbot thời tiết. Hãy viết lại câu hỏi sau theo cách tự nhiên khác, giữ nguyên ý nghĩa:
Câu gốc: {query}
Viết lại (1 câu, tiếng Việt, ngắn gọn):"""

    for ex in samples:
        try:
            resp = client.chat.completions.create(
                model=os.getenv("MODEL", "gpt-4o-mini"),
                messages=[{"role": "user", "content": REPHRASE_PROMPT.format(query=ex["input"])}],
                temperature=0.8,
                max_tokens=80,
            )
            rephrased = resp.choices[0].message.content.strip()
            if rephrased and rephrased != ex["input"]:
                new_ex = dict(ex)
                new_ex["input"] = rephrased
                # Update rewritten_query if present (it references original query context)
                if new_ex.get("output", {}).get("rewritten_query"):
                    # Keep rewritten_query as-is (it's the target standalone form)
                    pass
                augmented.append(new_ex)
        except Exception:
            continue

    print(f"LLM augmentation: generated {len(augmented)} additional examples")
    return augmented


def main(
    existing_train: str = "data/router/train_clean.jsonl",
    output_path: str = "data/router/multitask_train.jsonl",
    use_llm: bool = False,
    seed: int = 42,
) -> None:
    random.seed(seed)

    all_examples = []

    # 1. Existing routing data (routing only, context=null)
    routing_examples = generate_routing_examples(str(_ROOT / existing_train))
    all_examples.extend(routing_examples)

    # 2. Contextual rewrite examples
    rewrite_examples = generate_rewrite_examples()
    all_examples.extend(rewrite_examples)

    # 3. No-rewrite examples (standalone query with context)
    no_rewrite_examples = generate_no_rewrite_examples()
    all_examples.extend(no_rewrite_examples)

    # 4. Optional LLM augmentation
    if use_llm:
        llm_examples = augment_with_llm(rewrite_examples, n_augments=200)
        all_examples.extend(llm_examples)

    # Shuffle
    random.shuffle(all_examples)

    # Save
    out_path = _ROOT / output_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for ex in all_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    print(f"\nTotal: {len(all_examples)} examples")
    print(f"  - Routing only (context=null): {len(routing_examples)}")
    print(f"  - Rewrite examples:            {len(rewrite_examples)}")
    print(f"  - No-rewrite examples:         {len(no_rewrite_examples)}")
    print(f"Saved to: {out_path}")
    print("\nNext step: Update train_slm.ipynb to use this dataset with Qwen3-1.7B base model")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate multi-task SLM training data")
    parser.add_argument("--train", default="data/router/train_clean.jsonl",
                        help="Existing routing training data")
    parser.add_argument("--output", default="data/router/multitask_train.jsonl",
                        help="Output JSONL path")
    parser.add_argument("--use-llm", action="store_true",
                        help="Use GPT-4o-mini to augment with paraphrased examples")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    main(
        existing_train=args.train,
        output_path=args.output,
        use_llm=args.use_llm,
        seed=args.seed,
    )
