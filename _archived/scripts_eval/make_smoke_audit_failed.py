"""Tạo smoke CSV chỉ chứa các ID đánh Bucket C/D trong audit C1.

Trước đây dùng smoke_91 dựa trên claim của subagent (sai 41 IDs). Script này
parse trực tiếp 3 file audit để lấy danh sách thật.

Output: data/evaluation/v2/hanoi_weather_eval_v2_audit_failed.csv
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT_DIR = ROOT / "data" / "evaluation" / "v2" / "audit"
SRC = ROOT / "data" / "evaluation" / "v2" / "hanoi_weather_eval_v2_500.csv"
DST = ROOT / "data" / "evaluation" / "v2" / "hanoi_weather_eval_v2_audit_failed.csv"

# Bucket pattern: cover cả "Bucket: C", "Bucket C", "Bucket: B/C", "Bucket: D"
# Khi mixed ("B/C") → lấy ký tự cuối (consensus / final classification).
_BUCKET_RE = re.compile(r"\*\*Bucket\*?:?\s*\*?\s*([A-D](?:/[A-D])?)\*?")
_ID_HEADER_RE = re.compile(r"^### ID (\d+)\s*$", re.MULTILINE)


def _final_bucket(raw: str) -> str:
    """'B/C' → 'C'; 'D' → 'D'; etc."""
    return raw.split("/")[-1].strip()


def _parse_audit() -> dict[int, str]:
    """Return {qid: bucket} cho mọi ID có Bucket marker trong audit reports."""
    classification: dict[int, str] = {}
    for f in sorted(AUDIT_DIR.glob("report_c1_*.md")):
        text = f.read_text(encoding="utf-8")
        # split text on ### ID headers
        pos_ids = list(_ID_HEADER_RE.finditer(text))
        for i, m in enumerate(pos_ids):
            qid = int(m.group(1))
            start = m.end()
            end = pos_ids[i + 1].start() if i + 1 < len(pos_ids) else len(text)
            body = text[start:end]
            bm = _BUCKET_RE.search(body)
            if bm:
                classification[qid] = _final_bucket(bm.group(1))
    return classification


def _id_to_int(raw: str) -> int:
    if raw.startswith("v2_"):
        return int(raw[3:])
    return int(raw)


def main() -> None:
    classification = _parse_audit()
    failed = sorted(qid for qid, b in classification.items() if b in {"C", "D"})

    bucket_counts = {b: sum(1 for v in classification.values() if v == b) for b in "ABCD"}
    print(f"Audit classification: A={bucket_counts['A']} B={bucket_counts['B']} "
          f"C={bucket_counts['C']} D={bucket_counts['D']} "
          f"(total {sum(bucket_counts.values())})")
    print(f"Bucket C+D count: {len(failed)}")

    # Filter master CSV
    with SRC.open("r", encoding="utf-8") as f_in:
        reader = csv.DictReader(f_in)
        fieldnames = reader.fieldnames
        rows = [r for r in reader if _id_to_int(r["id"]) in set(failed)]
    print(f"Matched rows in master CSV: {len(rows)}")
    if len(rows) != len(failed):
        missing = set(failed) - {_id_to_int(r["id"]) for r in rows}
        print(f"WARNING: missing in CSV: {sorted(missing)}")

    with DST.open("w", encoding="utf-8", newline="") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows → {DST.relative_to(ROOT)}")

    # Print IDs split by bucket cho user verify
    print("\nBucket D (hard fail) IDs:", sorted(qid for qid, b in classification.items() if b == "D"))
    print("\nBucket C (partial fail) IDs:", sorted(qid for qid, b in classification.items() if b == "C"))


if __name__ == "__main__":
    main()
