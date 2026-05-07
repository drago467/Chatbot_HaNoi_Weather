"""Self-audit deterministic 79 ca: baseline vs post-fix, per qid + per cluster.

Output stdout markdown:
- Per qid: question, audit complaint excerpt, baseline tools+response, post tools+response
- Filter theo cluster P1-P7

Usage:
  python scripts/eval/audit_compare_79.py --cluster p1
  python scripts/eval/audit_compare_79.py --qids 269,270,316,379,484
  python scripts/eval/audit_compare_79.py --all
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT_DIR = ROOT / "data" / "evaluation" / "v2" / "audit"
DATASET = ROOT / "data" / "evaluation" / "v2" / "hanoi_weather_eval_v2_audit_failed.csv"
BASELINE_JSONL = ROOT / "data" / "evaluation" / "v2" / "run_results" / "c1_20260429_163155.jsonl"
POSTFIX_JSONL = ROOT / "data" / "evaluation" / "v2" / "run_results" / "c1_20260502_213048.jsonl"

# P-cluster ID assignments (from plan + audit verification)
CLUSTERS = {
    "p1": {
        "name": "Recursion (tuần qua / N ngày qua)",
        "ids": [269, 270, 316, 379, 484],
    },
    "p2": {
        "name": "Snapshot misuse for future query",
        "ids": [150, 288, 324, 435],  # IDs trong audit + smoke
    },
    "p3": {
        "name": "Hallucinated phenomena (sương mù/nắng/gió mùa)",
        "ids": [12, 23, 36, 60, 144, 152, 169, 196, 206, 232],
    },
    "p4": {
        "name": "Incomplete scope transparency",
        "ids": [313, 375, 411, 422, 423],
    },
    "p5": {
        "name": "Mislabel time frame / past-frame",
        "ids": [177, 197, 287, 406, 464],
    },
    "p6": {
        "name": "Bare weekday handling",
        "ids": [99, 119, 318, 455],
    },
    "p7": {
        "name": "Unit conversion + UV hourly absence",
        "ids": [345, 372],
    },
}


def _id_to_int(raw: str) -> int:
    if raw.startswith("v2_"):
        return int(raw[3:])
    return int(raw)


def _find_qid_format(qid_int: int, jsonl_qids: set) -> str | None:
    """JSONL có 2 format: '12' or 'v2_0212'."""
    for cand in (str(qid_int), f"v2_{qid_int:04d}"):
        if cand in jsonl_qids:
            return cand
    return None


def parse_audit_complaints() -> dict[int, dict]:
    """Return {qid_int: {bucket, body_excerpt}}."""
    out: dict[int, dict] = {}
    bucket_re = re.compile(r"\*\*Bucket\*?:?\s*\*?\s*([A-D](?:/[A-D])?)\*?")
    for f in sorted(AUDIT_DIR.glob("report_c1_*.md")):
        text = f.read_text(encoding="utf-8")
        # split on ### ID N
        chunks = re.split(r"\n### ID (\d+)\s*\n", text)
        # chunks = [preamble, id1, body1, id2, body2, ...]
        for i in range(1, len(chunks), 2):
            qid = int(chunks[i])
            body = chunks[i + 1] if i + 1 < len(chunks) else ""
            bm = bucket_re.search(body)
            bucket = bm.group(1).split("/")[-1] if bm else "?"
            out[qid] = {
                "bucket": bucket,
                "body": body.strip(),
            }
    return out


def load_jsonl_by_qid(path: Path) -> dict[str, dict]:
    out = {}
    if not path.exists():
        return out
    with path.open(encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            out[d["question_id"]] = d
    return out


def load_dataset_by_qid(path: Path) -> dict[int, dict]:
    out = {}
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[_id_to_int(r["id"])] = r
    return out


def render_qid(qid_int: int, audit: dict, dataset: dict, base: dict, new: dict) -> str:
    """Return markdown block for one qid."""
    base_qids = set(base.keys())
    new_qids = set(new.keys())
    cand = _find_qid_format(qid_int, base_qids | new_qids)
    if not cand:
        return f"### qid {qid_int}\n_(NOT FOUND in JSONL)_\n"

    ds_row = dataset.get(qid_int, {})
    audit_info = audit.get(qid_int, {"bucket": "?", "body": "_audit không có entry_"})
    base_row = base.get(cand, {})
    new_row = new.get(cand, {})

    def _fmt_response(r: dict) -> str:
        if not r:
            return "_(missing)_"
        if not r.get("success"):
            return f"❌ ERROR: {(r.get('error') or '')[:200]}"
        resp = r.get("response", "") or ""
        return resp[:600] + ("…" if len(resp) > 600 else "")

    def _fmt_tools(r: dict) -> str:
        if not r:
            return "_(missing)_"
        tc = r.get("tools_called") or []
        return ", ".join(tc) if tc else "_(no tools)_"

    # Tool acc check
    expected_tools = []
    try:
        expected_tools = json.loads(ds_row.get("expected_tools", "[]"))
    except (ValueError, TypeError):
        pass

    def _tool_match(r: dict) -> str:
        if not r or not r.get("success"):
            return "—"
        called = set(r.get("tools_called") or [])
        if not expected_tools:
            return "—"
        # Tool ACC: ít nhất 1 tool primary trong expected là called
        match = any(t in called for t in expected_tools)
        return "✓" if match else "✗"

    return (
        f"### qid {qid_int} (audit Bucket {audit_info['bucket']})\n"
        f"**Q**: {ds_row.get('question', '_(unknown)_')}\n\n"
        f"**Expected tools**: `{ds_row.get('expected_tools', '?')}`\n\n"
        f"**Audit complaint** (excerpt):\n```\n{audit_info['body'][:400]}\n```\n\n"
        f"| | Baseline | Post-fix |\n"
        f"|---|---|---|\n"
        f"| tools | `{_fmt_tools(base_row)}` | `{_fmt_tools(new_row)}` |\n"
        f"| tool_match | {_tool_match(base_row)} | {_tool_match(new_row)} |\n"
        f"| latency | {base_row.get('total_latency_ms', 0):.0f}ms | {new_row.get('total_latency_ms', 0):.0f}ms |\n\n"
        f"**Baseline response**:\n```\n{_fmt_response(base_row)}\n```\n\n"
        f"**Post-fix response**:\n```\n{_fmt_response(new_row)}\n```\n\n"
        f"---\n"
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cluster", default=None, help="p1..p7")
    ap.add_argument("--qids", default=None, help="comma-separated qids")
    ap.add_argument("--all", action="store_true", help="all 79")
    args = ap.parse_args()

    audit = parse_audit_complaints()
    dataset = load_dataset_by_qid(DATASET)
    base = load_jsonl_by_qid(BASELINE_JSONL)
    new = load_jsonl_by_qid(POSTFIX_JSONL)

    if args.cluster:
        ids = CLUSTERS[args.cluster]["ids"]
        print(f"## Cluster {args.cluster.upper()} — {CLUSTERS[args.cluster]['name']} ({len(ids)} qids)\n")
    elif args.qids:
        ids = [int(x) for x in args.qids.split(",")]
        print(f"## Custom qids: {ids}\n")
    elif args.all:
        ids = sorted(_id_to_int(r["id"]) for r in csv.DictReader(open(DATASET, encoding="utf-8")))
        print(f"## All {len(ids)} qids\n")
    else:
        ap.error("Need --cluster, --qids, or --all")

    for qid in ids:
        print(render_qid(qid, audit, dataset, base, new))


if __name__ == "__main__":
    main()
