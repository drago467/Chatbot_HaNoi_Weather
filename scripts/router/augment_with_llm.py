"""
Phase 1.2: LLM-based data augmentation for SLM Intent Router.

Reads seed_and_templates.jsonl, generates paraphrases via GPT-4o-mini,
adds hard negatives, and outputs augmented dataset.

Strategy:
1. For each (intent, scope) combo, generate paraphrases to reach target count
2. Focus more paraphrases on under-represented combos
3. Add hard negatives (ambiguous boundary cases)
4. Deduplicate final dataset

Output: data/router/raw/augmented.jsonl
"""

import asyncio
import json
import os
import random
import time
from collections import Counter, defaultdict
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()
random.seed(42)

ROOT = Path(__file__).resolve().parent.parent.parent
INPUT_PATH = ROOT / "data" / "router" / "raw" / "seed_and_templates.jsonl"
OUTPUT_PATH = ROOT / "data" / "router" / "raw" / "augmented.jsonl"
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────
TARGET_PER_COMBO = 30  # Target samples per (intent, scope) combo
PARAPHRASES_PER_BATCH = 5  # How many paraphrases to request per LLM call
MAX_CONCURRENT = 10  # Max concurrent API calls
MODEL = os.getenv("MODEL", "gpt-4o-mini-2024-07-18")

client = AsyncOpenAI(
    api_key=os.getenv("API_KEY"),
    base_url=os.getenv("API_BASE"),
)

# System prompt for paraphrase generation
PARAPHRASE_SYSTEM = """Bạn là chuyên gia ngôn ngữ tiếng Việt. Nhiệm vụ: tạo các câu hỏi diễn đạt lại (paraphrase) cho câu hỏi thời tiết.

Yêu cầu:
1. GIỮ NGUYÊN ý nghĩa (intent) và phạm vi địa điểm (scope) của câu gốc
2. THAY ĐỔI cách diễn đạt: dùng từ đồng nghĩa, đổi cấu trúc câu, thay đổi mức độ formal/informal
3. Giữ tự nhiên như người Việt nói hàng ngày (có thể dùng tiếng lóng, viết tắt nhẹ)
4. KHÔNG thay đổi địa điểm (nếu câu gốc nói về quận X thì paraphrase cũng phải về quận X)
5. KHÔNG thay đổi thời gian cụ thể (nếu "hôm nay" thì giữ "hôm nay", nhưng có thể đổi "hôm nay" thành "bữa nay")
6. Mỗi câu paraphrase phải KHÁC BIỆT rõ ràng với nhau

Trả về JSON array, mỗi phần tử là một string (câu hỏi paraphrase)."""

# Hard negatives: ambiguous cases near intent boundaries
HARD_NEGATIVES = [
    # rain_query vs hourly_forecast boundary
    {"q": "Chiều nay mưa lúc nào nhỉ?", "intent": "rain_query", "scope": "city"},
    {"q": "Mấy giờ chiều nay mưa?", "intent": "rain_query", "scope": "city"},
    {"q": "Chiều nay trời thế nào, có mưa không?", "intent": "rain_query", "scope": "city"},

    # temperature_query vs current_weather boundary
    {"q": "Trời nóng quá, bao nhiêu độ rồi?", "intent": "temperature_query", "scope": "city"},
    {"q": "Nóng thế này là bao nhiêu độ?", "intent": "temperature_query", "scope": "city"},

    # activity_weather vs smalltalk_weather boundary
    {"q": "Hôm nay đi chơi được không?", "intent": "activity_weather", "scope": "city"},
    {"q": "Hôm nay có đi ra ngoài được không?", "intent": "activity_weather", "scope": "city"},
    {"q": "Thời tiết ổn không, mình tính đi dạo?", "intent": "activity_weather", "scope": "city"},

    # smalltalk_weather vs activity_weather boundary
    {"q": "Hôm nay mặc gì đi làm?", "intent": "smalltalk_weather", "scope": "city"},
    {"q": "Đi làm hôm nay mang ô không nhỉ?", "intent": "smalltalk_weather", "scope": "city"},

    # seasonal_context vs current_weather boundary
    {"q": "Hôm nay nóng hơn mấy hôm trước không?", "intent": "seasonal_context", "scope": "city"},
    {"q": "Trời gần đây lạnh bất thường nhỉ?", "intent": "seasonal_context", "scope": "city"},
    {"q": "Mấy hôm nay trời thay đổi liên tục nhỉ?", "intent": "seasonal_context", "scope": "city"},

    # seasonal_context vs historical_weather boundary
    {"q": "Tuần trước so với tuần này khác nhau thế nào?", "intent": "seasonal_context", "scope": "city"},

    # weather_alert vs weather_overview boundary
    {"q": "Hôm nay thời tiết có gì đặc biệt không?", "intent": "weather_alert", "scope": "city"},
    {"q": "Có gì cần lưu ý về thời tiết không?", "intent": "weather_alert", "scope": "city"},

    # expert_weather_param vs current_weather boundary
    {"q": "Ngoài trời bao nhiêu độ, có nóng lắm không?", "intent": "current_weather", "scope": "city"},
    {"q": "Gió mạnh bao nhiêu km/h?", "intent": "wind_query", "scope": "city"},

    # location_comparison vs current_weather boundary
    {"q": "Quận nào mát nhất để đi dạo?", "intent": "location_comparison", "scope": "city"},

    # Multi-intent: pick primary
    {"q": "Chiều nay mưa không, nên mặc gì đi?", "intent": "rain_query", "scope": "city"},
    {"q": "Ngày mai trời nóng bao nhiêu, có nên đi chạy bộ?", "intent": "activity_weather", "scope": "city"},
    {"q": "Hôm nay gió mạnh không, đi đạp xe được không?", "intent": "activity_weather", "scope": "city"},

    # Out-of-Hanoi → smalltalk
    {"q": "Thời tiết Sài Gòn thế nào?", "intent": "smalltalk_weather", "scope": "city"},
    {"q": "Hải Phòng hôm nay có mưa không?", "intent": "smalltalk_weather", "scope": "city"},
    {"q": "So sánh thời tiết Hà Nội và Đà Nẵng", "intent": "smalltalk_weather", "scope": "city"},

    # Non-weather → smalltalk
    {"q": "Mấy giờ rồi?", "intent": "smalltalk_weather", "scope": "city"},
    {"q": "Hôm nay là thứ mấy?", "intent": "smalltalk_weather", "scope": "city"},
    {"q": "Tạm biệt nhé!", "intent": "smalltalk_weather", "scope": "city"},
    {"q": "Cảm ơn bạn nhiều!", "intent": "smalltalk_weather", "scope": "city"},

    # Implicit scope detection
    {"q": "Bên Ba Đình mưa chưa tạnh?", "intent": "rain_query", "scope": "district"},
    {"q": "Sân bay Nội Bài có sương mù không?", "intent": "humidity_fog_query", "scope": "poi"},
    {"q": "Khu Hồ Tây tối nay thế nào?", "intent": "current_weather", "scope": "poi"},
    {"q": "Mình ở Hoàng Mai, ngoài trời nóng không?", "intent": "temperature_query", "scope": "district"},
    {"q": "Ở đây trời thế nào?", "intent": "current_weather", "scope": "city"},  # ambiguous → city fallback

    # Colloquial/informal
    {"q": "Trời có mưa ko?", "intent": "rain_query", "scope": "city"},
    {"q": "Nóng vl, bao h mát?", "intent": "temperature_query", "scope": "city"},
    {"q": "Trời đẹp k bạn?", "intent": "smalltalk_weather", "scope": "city"},
    {"q": "Hôm nay ổn k ta?", "intent": "smalltalk_weather", "scope": "city"},
    {"q": "Mưa to k bạn ơi?", "intent": "rain_query", "scope": "city"},
    {"q": "Nắng quá đi, có bớt k?", "intent": "temperature_query", "scope": "city"},

    # Typo-like/abbreviated
    {"q": "Nhiet do ha noi bao nhieu?", "intent": "temperature_query", "scope": "city"},
    {"q": "thoi tiet hom nay the nao", "intent": "current_weather", "scope": "city"},
]


def load_existing() -> list[dict]:
    """Load seed_and_templates.jsonl."""
    samples = []
    with open(INPUT_PATH, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))
    return samples


def get_system_prompt_from_sample(sample: dict) -> str:
    """Extract system prompt from a sample."""
    return sample["messages"][0]["content"]


def group_by_combo(samples: list[dict]) -> dict[tuple, list[dict]]:
    """Group samples by (intent, scope)."""
    groups = defaultdict(list)
    for s in samples:
        key = (s["metadata"]["intent"], s["metadata"]["scope"])
        groups[key].append(s)
    return dict(groups)


async def generate_paraphrases(
    questions: list[str],
    intent: str,
    scope: str,
    n: int = 5,
    semaphore: asyncio.Semaphore = None,
) -> list[str]:
    """Generate N paraphrases for a batch of example questions."""
    examples_str = "\n".join(f"- {q}" for q in questions[:6])

    scope_vi = {
        "city": "toàn Hà Nội / không rõ địa điểm",
        "district": "quận/huyện cụ thể",
        "ward": "phường/xã cụ thể",
        "poi": "địa điểm nổi tiếng cụ thể",
    }
    intent_vi = {
        "current_weather": "hỏi thời tiết hiện tại",
        "hourly_forecast": "dự báo theo giờ",
        "daily_forecast": "dự báo theo ngày",
        "weather_overview": "tổng quan thời tiết",
        "rain_query": "hỏi về mưa",
        "temperature_query": "hỏi về nhiệt độ",
        "wind_query": "hỏi về gió",
        "humidity_fog_query": "hỏi về độ ẩm/sương mù",
        "historical_weather": "thời tiết quá khứ",
        "location_comparison": "so sánh địa điểm",
        "activity_weather": "thời tiết cho hoạt động",
        "expert_weather_param": "thông số kỹ thuật thời tiết",
        "weather_alert": "cảnh báo thời tiết",
        "seasonal_context": "so sánh/xu hướng thời tiết theo mùa/ngày",
        "smalltalk_weather": "nói chuyện phiếm, ngoài phạm vi, chào hỏi",
    }

    user_msg = (
        f"Intent: {intent} ({intent_vi.get(intent, '')})\n"
        f"Scope: {scope} ({scope_vi.get(scope, '')})\n\n"
        f"Các câu mẫu:\n{examples_str}\n\n"
        f"Tạo {n} câu hỏi paraphrase MỚI, khác biệt với các câu mẫu. "
        f"Trả về JSON array gồm {n} string."
    )

    if semaphore:
        async with semaphore:
            return await _call_api(user_msg)
    return await _call_api(user_msg)


async def _call_api(user_msg: str, retries: int = 3) -> list[str]:
    for attempt in range(retries):
        try:
            resp = await client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": PARAPHRASE_SYSTEM},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.9,
                max_tokens=1024,
            )
            content = resp.choices[0].message.content.strip()
            # Parse JSON array from response
            # Handle markdown code blocks
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            result = json.loads(content)
            if isinstance(result, list):
                return [str(q).strip() for q in result if q]
            return []
        except Exception as e:
            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)
            else:
                print(f"  [WARN] API call failed after {retries} retries: {e}")
                return []


async def augment_combo(
    intent: str,
    scope: str,
    existing_questions: list[str],
    target: int,
    system_prompt: str,
    semaphore: asyncio.Semaphore,
) -> list[dict]:
    """Augment a single (intent, scope) combo to reach target count."""
    needed = target - len(existing_questions)
    if needed <= 0:
        return []

    new_samples = []
    seen = set(existing_questions)

    # Generate in batches
    batch_count = (needed + PARAPHRASES_PER_BATCH - 1) // PARAPHRASES_PER_BATCH
    # Add extra batches for dedup losses
    batch_count = min(batch_count + 2, batch_count * 2)

    tasks = []
    for _ in range(batch_count):
        # Sample a few existing questions as examples
        examples = random.sample(existing_questions, min(6, len(existing_questions)))
        tasks.append(generate_paraphrases(examples, intent, scope, PARAPHRASES_PER_BATCH, semaphore))

    results = await asyncio.gather(*tasks)

    for paraphrases in results:
        for q in paraphrases:
            if q not in seen and len(new_samples) < needed:
                seen.add(q)
                new_samples.append({
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": q},
                        {"role": "assistant", "content": json.dumps(
                            {"intent": intent, "scope": scope}, ensure_ascii=False
                        )},
                    ],
                    "metadata": {"source": "llm_paraphrase", "intent": intent, "scope": scope},
                })

    return new_samples


def make_hard_negative_samples(system_prompt: str) -> list[dict]:
    """Convert hard negatives to training samples."""
    samples = []
    for hn in HARD_NEGATIVES:
        samples.append({
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": hn["q"]},
                {"role": "assistant", "content": json.dumps(
                    {"intent": hn["intent"], "scope": hn["scope"]}, ensure_ascii=False
                )},
            ],
            "metadata": {"source": "hard_negative", "intent": hn["intent"], "scope": hn["scope"]},
        })
    return samples


def deduplicate(samples: list[dict]) -> list[dict]:
    """Remove duplicates, keeping first (prioritize seed > template > hard_negative > llm)."""
    priority = {"seed": 0, "template": 1, "hard_negative": 2, "llm_paraphrase": 3}
    samples.sort(key=lambda s: priority.get(s["metadata"]["source"], 9))
    seen = set()
    result = []
    for s in samples:
        q = s["messages"][1]["content"].strip().lower()
        if q not in seen:
            seen.add(q)
            result.append(s)
    return result


def print_distribution(samples: list[dict], label: str = ""):
    combo_counts = Counter()
    intent_counts = Counter()
    scope_counts = Counter()
    source_counts = Counter()
    for s in samples:
        meta = s["metadata"]
        combo_counts[(meta["intent"], meta["scope"])] += 1
        intent_counts[meta["intent"]] += 1
        scope_counts[meta["scope"]] += 1
        source_counts[meta["source"]] += 1

    print(f"\n{'='*60}")
    print(f"  {label}: {len(samples)} samples")
    print(f"{'='*60}")

    print(f"\n  Sources: {dict(sorted(source_counts.items()))}")

    print(f"\n  Intents ({len(intent_counts)}):")
    for k, v in sorted(intent_counts.items(), key=lambda x: -x[1]):
        print(f"    {k:30s} {v:4d}")

    print(f"\n  Scopes ({len(scope_counts)}):")
    for k, v in sorted(scope_counts.items(), key=lambda x: -x[1]):
        print(f"    {k:15s} {v:4d}")

    vals = list(combo_counts.values())
    print(f"\n  Intent×Scope combos: {len(combo_counts)}, "
          f"min={min(vals)}, max={max(vals)}, avg={sum(vals)/len(vals):.1f}")


async def main():
    print("Phase 1.2: LLM Augmentation for SLM Intent Router")
    print("=" * 60)

    # Step 1: Load existing data
    print("\n[1/4] Loading existing samples...")
    existing = load_existing()
    system_prompt = get_system_prompt_from_sample(existing[0])
    groups = group_by_combo(existing)
    print(f"  Loaded {len(existing)} samples across {len(groups)} combos")

    # Step 2: Add hard negatives
    print(f"\n[2/4] Adding {len(HARD_NEGATIVES)} hard negatives...")
    hard_neg_samples = make_hard_negative_samples(system_prompt)

    # Step 3: Generate LLM paraphrases
    print(f"\n[3/4] Generating LLM paraphrases (target {TARGET_PER_COMBO}/combo)...")
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    tasks = []
    combos_needing_aug = []
    for (intent, scope), samples in sorted(groups.items()):
        questions = [s["messages"][1]["content"] for s in samples]
        # Also count hard negatives for this combo
        hn_count = sum(1 for hn in HARD_NEGATIVES
                       if hn["intent"] == intent and hn["scope"] == scope)
        current = len(questions) + hn_count
        if current < TARGET_PER_COMBO:
            combos_needing_aug.append((intent, scope, current, TARGET_PER_COMBO))
            tasks.append(augment_combo(
                intent, scope, questions, TARGET_PER_COMBO, system_prompt, semaphore
            ))

    print(f"  {len(combos_needing_aug)} combos need augmentation:")
    for intent, scope, current, target in combos_needing_aug:
        print(f"    {intent:30s} × {scope:10s}: {current:3d} → {target}")

    if tasks:
        print(f"\n  Running {len(tasks)} augmentation tasks...")
        start = time.time()
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start
        total_new = sum(len(r) for r in results)
        print(f"  Generated {total_new} new paraphrases in {elapsed:.1f}s")
    else:
        results = []
        print("  No augmentation needed!")

    # Step 4: Merge everything
    print("\n[4/4] Merging and deduplicating...")
    all_samples = existing + hard_neg_samples
    for batch in results:
        all_samples.extend(batch)
    all_samples = deduplicate(all_samples)

    # Shuffle
    random.shuffle(all_samples)

    print_distribution(all_samples, "Final augmented dataset")

    # Save
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for s in all_samples:
            json.dump(s, f, ensure_ascii=False)
            f.write("\n")
    print(f"\n  Saved → {OUTPUT_PATH}")

    print(f"\n{'='*60}")
    print(f"  Done! Next: train/val/test split")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
