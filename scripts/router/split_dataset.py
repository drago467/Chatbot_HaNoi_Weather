"""
Phase 1.3: Split augmented dataset into train/val/test.

Stratified split by (intent, scope) to ensure balanced representation.
Split ratio: 80/10/10.

Output: data/router/train.jsonl, data/router/val.jsonl, data/router/test.jsonl
"""

import json
import random
from collections import Counter, defaultdict
from pathlib import Path

random.seed(42)

ROOT = Path(__file__).resolve().parent.parent.parent
INPUT_PATH = ROOT / "data" / "router" / "raw" / "augmented.jsonl"
OUTPUT_DIR = ROOT / "data" / "router"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_jsonl(path: Path) -> list[dict]:
    samples = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))
    return samples


def stratified_split(
    samples: list[dict],
    train_ratio: float = 0.80,
    val_ratio: float = 0.10,
) -> tuple[list[dict], list[dict], list[dict]]:
    """
    Stratified split by (intent, scope).
    Ensures each combo has at least 1 sample in val and test.
    Seed samples are prioritized for train (not leaked to val/test).
    """
    # Group by combo
    groups = defaultdict(list)
    for s in samples:
        key = (s["metadata"]["intent"], s["metadata"]["scope"])
        groups[key].append(s)

    train, val, test = [], [], []

    for key, group in sorted(groups.items()):
        # Separate seed from non-seed
        seed_samples = [s for s in group if s["metadata"]["source"] == "seed"]
        other_samples = [s for s in group if s["metadata"]["source"] != "seed"]
        random.shuffle(other_samples)

        n = len(group)
        n_val = max(1, round(n * val_ratio))
        n_test = max(1, round(n * val_ratio))  # test same size as val

        # Take val/test from non-seed first, then seed if not enough
        pool = other_samples + seed_samples
        random.shuffle(pool)

        # Ensure at least 1 in val and test
        test_set = pool[:n_test]
        val_set = pool[n_test:n_test + n_val]
        train_set = pool[n_test + n_val:]

        # Add any remaining seed samples to train if they weren't used
        used = set(id(s) for s in test_set + val_set)
        for s in seed_samples:
            if id(s) not in used and s not in train_set:
                train_set.append(s)

        train.extend(train_set)
        val.extend(val_set)
        test.extend(test_set)

    random.shuffle(train)
    random.shuffle(val)
    random.shuffle(test)

    return train, val, test


def save_jsonl(samples: list[dict], path: Path, strip_metadata: bool = False):
    """Save samples. Optionally strip metadata for final training files."""
    with open(path, "w", encoding="utf-8") as f:
        for s in samples:
            if strip_metadata:
                out = {"messages": s["messages"]}
            else:
                out = s
            json.dump(out, f, ensure_ascii=False)
            f.write("\n")


def print_split_stats(name: str, samples: list[dict]):
    combo_counts = Counter()
    source_counts = Counter()
    for s in samples:
        m = s["metadata"]
        combo_counts[(m["intent"], m["scope"])] += 1
        source_counts[m["source"]] += 1
    vals = list(combo_counts.values()) if combo_counts else [0]
    print(f"  {name:5s}: {len(samples):5d} samples | "
          f"{len(combo_counts)} combos | "
          f"min={min(vals)} max={max(vals)} avg={sum(vals)/max(len(vals),1):.1f} | "
          f"sources={dict(sorted(source_counts.items()))}")


def main():
    print("Phase 1.3: Train/Val/Test Split")
    print("=" * 60)

    samples = load_jsonl(INPUT_PATH)
    print(f"\nLoaded {len(samples)} samples from augmented.jsonl")

    train, val, test = stratified_split(samples)

    print(f"\nSplit results:")
    print_split_stats("Train", train)
    print_split_stats("Val", val)
    print_split_stats("Test", test)

    # Save with metadata (for analysis)
    save_jsonl(train, OUTPUT_DIR / "train.jsonl")
    save_jsonl(val, OUTPUT_DIR / "val.jsonl")
    save_jsonl(test, OUTPUT_DIR / "test.jsonl")

    # Also save training-ready format (no metadata, just messages)
    save_jsonl(train, OUTPUT_DIR / "train_clean.jsonl", strip_metadata=True)
    save_jsonl(val, OUTPUT_DIR / "val_clean.jsonl", strip_metadata=True)
    save_jsonl(test, OUTPUT_DIR / "test_clean.jsonl", strip_metadata=True)

    print(f"\nSaved to: {OUTPUT_DIR}")
    print(f"  With metadata: train.jsonl, val.jsonl, test.jsonl")
    print(f"  Clean (training): train_clean.jsonl, val_clean.jsonl, test_clean.jsonl")

    # Verify no leakage
    train_q = set(s["messages"][1]["content"] for s in train)
    val_q = set(s["messages"][1]["content"] for s in val)
    test_q = set(s["messages"][1]["content"] for s in test)

    leak_tv = train_q & val_q
    leak_tt = train_q & test_q
    leak_vt = val_q & test_q

    if leak_tv or leak_tt or leak_vt:
        print(f"\n  [WARN] Data leakage detected!")
        print(f"    Train∩Val: {len(leak_tv)}, Train∩Test: {len(leak_tt)}, Val∩Test: {len(leak_vt)}")
    else:
        print(f"\n  ✓ No data leakage between splits")


if __name__ == "__main__":
    main()
