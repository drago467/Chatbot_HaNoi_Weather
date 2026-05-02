"""Tạo smoke CSV chỉ chứa 91 IDs failed trong audit C1 (config production parity).

Subset:
- Bucket D (26 hard fail): 32, 56, 66, 74, 95, 105, 108, 119, 150, 167, 177, 197,
  202, 211, 212, 214, 227, 248, 269, 270, 303, 316, 345, 372, 379, 484
- Bucket C (65 partial): 12, 23, 33, 35, 36, 58, 60, 64, 86, 99, 114, 118, 123,
  129, 133, 138, 144, 168, 169, 175, 196, 198, 206, 209, 219, 232, 240, 256,
  262, 265, 266, 273, 274, 281, 282, 287, 291, 298, 304, 307, 319, 322, 323,
  324, 325, 329, 332, 344, 353, 362, 380, 382, 383, 389, 406, 419, 433, 435,
  436, 451, 455, 460, 464, 481, 500

Output: data/evaluation/v2/hanoi_weather_eval_v2_smoke91.csv
"""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "evaluation" / "v2" / "hanoi_weather_eval_v2_500.csv"
DST = ROOT / "data" / "evaluation" / "v2" / "hanoi_weather_eval_v2_smoke91.csv"

FAILED_IDS = sorted(set([
    # Bucket D — 26 hard fails
    32, 56, 66, 74, 95, 105, 108, 119, 150, 167, 177, 197,
    202, 211, 212, 214, 227, 248, 269, 270, 303, 316, 345, 372, 379,
    484,
    # Bucket C — 65 partials
    12, 23, 33, 35, 36, 58, 60, 64, 86, 99, 114, 118, 123,
    129, 133, 138, 144, 168, 169, 175, 196, 198,
    206, 209, 219, 232, 240, 256, 262, 265, 266, 273, 274,
    281, 282, 287, 291, 298, 304, 307, 319, 322, 323, 324,
    325, 329, 332, 344, 353, 362, 380, 382, 383, 389, 406, 419,
    433, 435, 436, 451, 455, 460, 464, 481, 500,
]))

assert len(FAILED_IDS) == 91, f"Expected 91, got {len(FAILED_IDS)}"


def _id_to_int(raw: str) -> int:
    """ID có 2 format: '1'..'199' (integer-only) hoặc 'v2_0200'..'v2_0500'."""
    if raw.startswith("v2_"):
        return int(raw[3:])
    return int(raw)


def main() -> None:
    with SRC.open("r", encoding="utf-8") as f_in:
        reader = csv.DictReader(f_in)
        fieldnames = reader.fieldnames
        rows = [r for r in reader if _id_to_int(r["id"]) in FAILED_IDS]
    if len(rows) != 91:
        raise SystemExit(f"Expected 91 rows, got {len(rows)}")
    with DST.open("w", encoding="utf-8", newline="") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows → {DST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
