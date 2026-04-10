"""
scripts/data/audit_smalltalk_labels.py
Manual audit of all smalltalk_weather samples in train + val sets.

Categorises each sample into one of:
  keep_smalltalk    → genuine greeting / farewell / identity / chatbot conversation
  relabel_activity  → umbrella / clothing / outfit advice → activity_weather
  relabel_seasonal  → "mùa này thế nào" → seasonal_context
  relabel_current   → "trời đẹp không" / "có nắng không" → current_weather
  relabel_rain      → "mai có mưa không" with implicit city → rain_query
  remove_oos        → non-Hanoi city (Đà Nẵng, HCM, Hải Phòng…) → remove
  remove_offtopic   → completely off-topic (time, day-of-week) → remove
  flag_anaphora     → anaphoric ref without context → ambiguous, keep for now

Output:
  data/evaluation/thesis_final/exp5/smalltalk_audit_report.csv
"""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = ROOT / "data/evaluation/thesis_final/exp5"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PATH = OUTPUT_DIR / "smalltalk_audit_report.csv"

# ── Manual classification rules ──────────────────────────────────────────────
# Applied via keyword matching (ordered, first match wins)

OOS_CITIES = ["Đà Nẵng", "da nang", "Hải Phòng", "hai phong", "TP.HCM", "HCM",
               "Sài Gòn", "Sai Gon", "Đà Lạt", "Da Lat"]

OFFTOPIC_PATTERNS = [
    "mấy giờ rồi", "may gio roi", "thứ mấy", "thu may",
    "Hôm nay là thứ", "hom nay la thu",
]

ACTIVITY_PATTERNS = [
    "mang theo ô", "mang theo o", "cần ô", "can o", "cần phòng mưa", "can phong mua",
    "mang áo khoác", "mang ao khoac", "cần áo khoác", "can ao khoac",
    "nên mặc", "nen mac", "mặc gì", "mac gi", "chọn đồ", "chon do",
    "trang phục", "trang phuc", "chọn trang phục", "ăn mặc",
    "cần ô không", "can o khong", "thủ sẵn ô", "thu san o",
    "phòng mưa", "phong mua", "nên mặc đồ", "mac ao mong",
    "mac ao day", "ao khoac co can", "ao khoac khong",
    "can mang ao khoac", "mang ao khoac khong", "mac ao phao",
    "chuan bi ao khoac",
]

SEASONAL_PATTERNS = [
    "mùa này thế nào", "mua nay the nao", "mùa này như thế nào",
    "mùa này ra sao", "mua nay the nao nhi",
    "thế nào nhỉ" ,  # combined with mùa
]

RAIN_PATTERNS = [
    "mai có mưa không", "mai co mua khong",
    "Không biết mai có mưa", "khong biet mai co mua",
]

CURRENT_PATTERNS = [
    "trời đẹp không", "troi dep khong", "có nắng không", "co nang khong",
    "trời trong xanh không", "troi trong xanh", "có trong lành không",
    "ra sao nhỉ", "thế nào nhỉ",
    "dễ chịu không", "de chiu khong", "de chiu ghe",
    "Hôm nay ổn", "hom nay on", "thời tiết ở đó", "thoi tiet o do",
    "ra sao", "thế nào",
]

ANAPHORA_PATTERNS = [
    "chỗ đó", "cho do", "Nơi đó", "noi do", "ở đó", "o do",
    "chỗ đó có", "Thời tiết ở đó", "thoi tiet o do",
]

GENUINE_SMALLTALK = [
    "xin chào", "Xin chào", "chào bạn", "chao ban",
    "tạm biệt", "tam biet", "cảm ơn", "cam on", "thank",
    "bạn là ai", "ban la ai", "Bạn là ai",
    "bạn có thể giúp", "ban co the giup",
    "bạn giúp mình được gì", "ban giup minh duoc gi",
    "hôm nay ổn k", "Hôm nay ổn k",
    "trời đẹp k", "Trời đẹp k",
    "tuyệt vời", "tuyet voi",
    "có buồn không", "co buon khong",
    "mát mẻ nhỉ", "mat me nhi",
    "có sao không", "co sao khong",  # stargazing
    "ngắm sao", "ngam sao",
    "Tối nay trời có đẹp", "toi nay troi co dep",
]


def classify(query: str) -> tuple[str, str]:
    """Return (category, reason)."""
    q_lower = query.lower()

    # Out-of-scope cities
    for city in OOS_CITIES:
        if city.lower() in q_lower:
            return "remove_oos", f"Non-Hanoi location: {city}"

    # Completely off-topic
    for pat in OFFTOPIC_PATTERNS:
        if pat.lower() in q_lower:
            return "remove_offtopic", f"Off-topic pattern: {pat}"

    # Check seasonal BEFORE activity (avoid "mùa này thế nào" being flagged by "thế nào nhỉ")
    if any(p.lower() in q_lower for p in ["mùa này", "mua nay"]):
        return "relabel_seasonal", "Seasonal pattern: mùa này"

    # Activity/clothing
    for pat in ACTIVITY_PATTERNS:
        if pat.lower() in q_lower:
            return "relabel_activity", f"Activity pattern: {pat}"

    # Rain query
    for pat in RAIN_PATTERNS:
        if pat.lower() in q_lower:
            return "relabel_rain", f"Rain pattern: {pat}"

    # Anaphora (no context)
    for pat in ANAPHORA_PATTERNS:
        if pat.lower() in q_lower:
            return "flag_anaphora", f"Anaphoric reference: {pat}"

    # Genuine smalltalk
    for pat in GENUINE_SMALLTALK:
        if pat.lower() in q_lower:
            return "keep_smalltalk", f"Genuine smalltalk: {pat}"

    # Subjective weather comment → current_weather
    for pat in CURRENT_PATTERNS:
        if pat.lower() in q_lower:
            return "relabel_current", f"Weather assessment: {pat}"

    return "keep_smalltalk", "No specific pattern matched, default smalltalk"


def load_jsonl(path: Path) -> list[dict]:
    samples = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            d = json.loads(line)
            d["_line"] = i
            samples.append(d)
    return samples


def main():
    train = load_jsonl(ROOT / "data/router/multitask_train_v3.jsonl")
    val = load_jsonl(ROOT / "data/router/multitask_val_v3.jsonl")

    rows = []
    for split, data in [("train", train), ("val", val)]:
        for d in data:
            if d["output"]["intent"] != "smalltalk_weather":
                continue
            q = d["input"].strip()
            cat, reason = classify(q)
            rows.append({
                "split": split,
                "line": d["_line"],
                "query": q,
                "confidence": d["output"].get("confidence", ""),
                "scope": d["output"].get("scope", ""),
                "category": cat,
                "reason": reason,
                "suggested_intent": {
                    "keep_smalltalk": "smalltalk_weather",
                    "relabel_activity": "activity_weather",
                    "relabel_seasonal": "seasonal_context",
                    "relabel_current": "current_weather",
                    "relabel_rain": "rain_query",
                    "remove_oos": "REMOVE",
                    "remove_offtopic": "REMOVE",
                    "flag_anaphora": "smalltalk_weather (ambiguous)",
                }[cat],
            })

    # Save CSV
    with open(REPORT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["split", "line", "query", "confidence",
                                                "scope", "category", "suggested_intent", "reason"])
        writer.writeheader()
        writer.writerows(rows)

    # Summary
    from collections import Counter
    cats = Counter(r["category"] for r in rows)
    train_cats = Counter(r["category"] for r in rows if r["split"] == "train")
    val_cats = Counter(r["category"] for r in rows if r["split"] == "val")

    print(f"\nSmaltalk Audit Report — {len(rows)} samples total")
    print(f"  Train: {sum(train_cats.values())} | Val: {sum(val_cats.values())}")
    print()
    print(f"{'Category':<25} {'Train':>6} {'Val':>6} {'Total':>7}  Action")
    print("-" * 70)
    for cat in ["keep_smalltalk", "flag_anaphora", "relabel_activity",
                "relabel_seasonal", "relabel_current", "relabel_rain",
                "remove_oos", "remove_offtopic"]:
        t = train_cats.get(cat, 0)
        v = val_cats.get(cat, 0)
        action = {
            "keep_smalltalk": "Keep as-is",
            "flag_anaphora": "Keep (ambiguous, mark for review)",
            "relabel_activity": "→ activity_weather",
            "relabel_seasonal": "→ seasonal_context",
            "relabel_current": "→ current_weather",
            "relabel_rain": "→ rain_query",
            "remove_oos": "REMOVE (non-Hanoi)",
            "remove_offtopic": "REMOVE (off-topic)",
        }[cat]
        print(f"  {cat:<23} {t:>6} {v:>6} {t+v:>7}  {action}")

    print("-" * 70)
    total_remove = cats.get("remove_oos", 0) + cats.get("remove_offtopic", 0)
    total_relabel = (cats.get("relabel_activity", 0) + cats.get("relabel_seasonal", 0)
                     + cats.get("relabel_current", 0) + cats.get("relabel_rain", 0))
    total_keep = cats.get("keep_smalltalk", 0) + cats.get("flag_anaphora", 0)
    print(f"  {'TOTAL REMOVE':<23} {total_remove:>13}  Out-of-scope / off-topic")
    print(f"  {'TOTAL RELABEL':<23} {total_relabel:>13}  Wrong intent label")
    print(f"  {'TOTAL KEEP':<23} {total_keep:>13}  Correct smalltalk_weather")
    print()
    print(f"Saved: {REPORT_PATH}")
    print()
    print("NOTE: This audit is for THESIS ANALYSIS only.")
    print("The model was trained on the original labels — do NOT re-train.")
    print("Use findings to explain F1=0.833 for smalltalk_weather in Exp 1.")


if __name__ == "__main__":
    main()
