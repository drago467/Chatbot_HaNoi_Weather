"""Experiment 1 — Router Comparison (RQ1).

Compare 4 router configurations on 672 independent validation samples:
  R1. Qwen3-4B fine-tuned (LoRA, Ollama)      — proposed method
  R2. Qwen3-4B zero-shot  (Ollama base model)  — ablation: value of fine-tuning
  R3. GPT-4o-mini zero-shot (API)               — small LLM baseline
  R4. GPT-4o zero-shot      (API)               — upper bound

Methodology references:
  - LoRA (Hu et al., 2021): FT vs zero-shot on same base model
  - RouteLLM (Ong et al., 2024): strong/weak model pair comparison
  - Hybrid LLM (Ding et al., ICLR 2024): small-local vs large-cloud
  - McNemar test for paired comparison on binary outcomes

Usage:
  # Run all configs:
  python scripts/experiments/exp1_router_comparison.py

  # Run specific configs:
  python scripts/experiments/exp1_router_comparison.py --configs R1 R3 R4

  # Dry run (5 samples):
  python scripts/experiments/exp1_router_comparison.py --dry-run

  # Skip slow configs:
  python scripts/experiments/exp1_router_comparison.py --configs R1 --skip-scope
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import numpy as np

# ── Project root ──
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from app.agent.router.config import ROUTER_SYSTEM_PROMPT, VALID_INTENTS, VALID_SCOPES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Output directory ──
OUTPUT_DIR = ROOT / "data" / "evaluation" / "thesis_final" / "exp1_router"

# ── Config constants ──
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_FT_MODEL = os.getenv("OLLAMA_MODEL", "hanoi-weather-router-v4")

# R2: Qwen3-4B zero-shot via API (NOT Ollama — insufficient RAM to run 2 models simultaneously)
# Set in .env: QWEN3_4B_API_KEY, QWEN3_4B_API_BASE, QWEN3_4B_MODEL
QWEN3_4B_API_KEY  = os.getenv("QWEN3_4B_API_KEY", "")
QWEN3_4B_API_BASE = os.getenv("QWEN3_4B_API_BASE", "")
QWEN3_4B_MODEL    = os.getenv("QWEN3_4B_MODEL", "qwen3-4b")

# R3: GPT-4o-mini zero-shot (gpt1.shupremium.com)
GPT4O_MINI_API_KEY  = os.getenv("JUDGE_API_KEY", os.getenv("API_KEY", ""))
GPT4O_MINI_API_BASE = os.getenv("JUDGE_API_BASE", os.getenv("API_BASE", ""))
GPT4O_MINI_MODEL    = os.getenv("JUDGE_MODEL", "gpt-4o-mini-2024-07-18")

# R4: GPT-4o zero-shot (upper bound)
GPT4O_API_KEY  = os.getenv("GPT4O_API_KEY", GPT4O_MINI_API_KEY)
GPT4O_API_BASE = os.getenv("GPT4O_API_BASE", GPT4O_MINI_API_BASE)
GPT4O_MODEL    = os.getenv("GPT4O_MODEL", "gpt-4o-2024-11-20")


# ═══════════════════════════════════════════════════════════════════
# Data classes
# ═══════════════════════════════════════════════════════════════════

@dataclass
class Sample:
    idx: int
    input_text: str
    context: dict | None
    expected_intent: str
    expected_scope: str

@dataclass
class Prediction:
    intent: str
    scope: str
    confidence: float
    latency_ms: float
    raw_response: str = ""
    error: str | None = None


# ═══════════════════════════════════════════════════════════════════
# Router backends
# ═══════════════════════════════════════════════════════════════════

def _build_user_message(input_text: str, context: dict | None) -> str:
    """Build user message, injecting context if available (same as SLMRouter)."""
    if context is None:
        return input_text
    context_str = json.dumps(context, ensure_ascii=False)
    return f"[CONTEXT: {context_str}]\n{input_text}"


def _parse_json_response(text: str) -> dict | None:
    """Extract JSON from model output."""
    import re
    text = text.strip()
    # Remove think tags (Qwen3 may output <think>...</think>)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[^{}]+\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


class OllamaRouter:
    """Router using Ollama /api/chat endpoint."""

    def __init__(self, model: str, label: str):
        self.model = model
        self.label = label
        self._client = httpx.Client(timeout=120.0)  # cold start on CPU can take ~50s

    def predict(self, input_text: str, context: dict | None) -> Prediction:
        user_msg = _build_user_message(input_text, context)
        t0 = time.perf_counter()
        try:
            resp = self._client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                        {"role": "user", "content": user_msg},
                    ],
                    "stream": False,
                    "options": {"temperature": 0.0, "num_predict": 128},
                },
            )
            resp.raise_for_status()
            raw = resp.json().get("message", {}).get("content", "")
        except Exception as e:
            return Prediction(
                intent="", scope="", confidence=0.0,
                latency_ms=_elapsed_ms(t0), error=str(e),
            )

        latency = _elapsed_ms(t0)
        parsed = _parse_json_response(raw)
        if parsed is None:
            return Prediction(
                intent="", scope="", confidence=0.0,
                latency_ms=latency, raw_response=raw[:200],
                error=f"json_parse_error",
            )
        return Prediction(
            intent=parsed.get("intent", ""),
            scope=parsed.get("scope", "city"),
            confidence=float(parsed.get("confidence", 0.0)),
            latency_ms=latency,
            raw_response=raw[:200],
        )

    def close(self):
        self._client.close()


class OpenAIRouter:
    """Router using OpenAI-compatible /v1/chat/completions endpoint.

    Includes exponential backoff retry for 429/5xx errors (up to MAX_RETRIES).
    """

    MAX_RETRIES = 5
    BASE_DELAY = 2.0  # seconds — doubles each retry (2, 4, 8, 16, 32)

    def __init__(self, api_key: str, api_base: str, model: str, label: str):
        self.api_key = api_key
        self.api_base = api_base.rstrip("/")
        self.model = model
        self.label = label
        self._client = httpx.Client(timeout=60.0)

    def predict(self, input_text: str, context: dict | None) -> Prediction:
        user_msg = _build_user_message(input_text, context)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            "temperature": 0.0,
            "max_tokens": 150,
        }
        # GPT models: enable JSON mode
        if "gpt-4o" in self.model:
            payload["response_format"] = {"type": "json_object"}
        # Qwen3 models via sv1: must disable thinking for non-streaming calls
        if "qwen3" in self.model.lower():
            payload["extra_body"] = {"enable_thinking": False}
            # Some providers use top-level param instead of extra_body
            payload["enable_thinking"] = False

        t0 = time.perf_counter()
        last_error = None

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                resp = self._client.post(
                    f"{self.api_base}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                # Retry on 429 (rate limit) or 5xx (server error)
                if resp.status_code == 429 or resp.status_code >= 500:
                    delay = self.BASE_DELAY * (2 ** attempt)
                    last_error = f"HTTP {resp.status_code}"
                    if attempt < self.MAX_RETRIES:
                        logger.debug(
                            "[%s] %s — retry %d/%d in %.1fs",
                            self.label, last_error, attempt + 1, self.MAX_RETRIES, delay,
                        )
                        time.sleep(delay)
                        continue
                    else:
                        return Prediction(
                            intent="", scope="", confidence=0.0,
                            latency_ms=_elapsed_ms(t0),
                            error=f"{last_error} after {self.MAX_RETRIES} retries",
                        )

                resp.raise_for_status()
                data = resp.json()
                raw = data["choices"][0]["message"]["content"]
                break  # success

            except Exception as e:
                last_error = str(e)
                if attempt < self.MAX_RETRIES:
                    delay = self.BASE_DELAY * (2 ** attempt)
                    logger.debug("[%s] Error: %s — retry %d/%d in %.1fs",
                                 self.label, last_error, attempt + 1, self.MAX_RETRIES, delay)
                    time.sleep(delay)
                    continue
                return Prediction(
                    intent="", scope="", confidence=0.0,
                    latency_ms=_elapsed_ms(t0),
                    error=f"{last_error} after {self.MAX_RETRIES} retries",
                )
        else:
            # All retries exhausted (shouldn't reach here, but safety net)
            return Prediction(
                intent="", scope="", confidence=0.0,
                latency_ms=_elapsed_ms(t0), error=f"max retries: {last_error}",
            )

        latency = _elapsed_ms(t0)
        parsed = _parse_json_response(raw)
        if parsed is None:
            return Prediction(
                intent="", scope="", confidence=0.0,
                latency_ms=latency, raw_response=raw[:200],
                error="json_parse_error",
            )
        return Prediction(
            intent=parsed.get("intent", ""),
            scope=parsed.get("scope", "city"),
            confidence=float(parsed.get("confidence", 0.0)),
            latency_ms=latency,
            raw_response=raw[:200],
        )

    def close(self):
        self._client.close()


# ═══════════════════════════════════════════════════════════════════
# Metrics
# ═══════════════════════════════════════════════════════════════════

def wilson_ci(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score 95% CI for binomial proportion."""
    if total == 0:
        return (0.0, 0.0)
    p = successes / total
    denom = 1 + z**2 / total
    center = p + z**2 / (2 * total)
    spread = z * np.sqrt(p * (1 - p) / total + z**2 / (4 * total**2))
    lo = (center - spread) / denom
    hi = (center + spread) / denom
    return (max(0.0, lo), min(1.0, hi))


def mcnemar_test(correct_a: list[bool], correct_b: list[bool]) -> dict:
    """McNemar's test for paired comparison.

    Returns dict with chi2 statistic, p-value, and contingency table counts.
    """
    from scipy.stats import chi2 as chi2_dist

    n = len(correct_a)
    assert n == len(correct_b), "Lists must have same length"

    # Contingency table:
    # b=1,b=0 vs a=1,a=0
    b_both = sum(1 for a, b in zip(correct_a, correct_b) if a and b)      # both correct
    c_only_a = sum(1 for a, b in zip(correct_a, correct_b) if a and not b) # only A correct
    b_only_b = sum(1 for a, b in zip(correct_a, correct_b) if not a and b) # only B correct
    d_neither = sum(1 for a, b in zip(correct_a, correct_b) if not a and not b)

    # McNemar statistic (with continuity correction)
    discordant = c_only_a + b_only_b
    if discordant == 0:
        return {
            "chi2": 0.0, "p_value": 1.0,
            "both_correct": b_both, "only_a_correct": c_only_a,
            "only_b_correct": b_only_b, "both_wrong": d_neither,
            "note": "no discordant pairs",
        }

    chi2 = (abs(c_only_a - b_only_b) - 1) ** 2 / discordant
    p_value = 1 - chi2_dist.cdf(chi2, df=1)

    return {
        "chi2": round(float(chi2), 4),
        "p_value": round(float(p_value), 6),
        "both_correct": int(b_both),
        "only_a_correct": int(c_only_a),
        "only_b_correct": int(b_only_b),
        "both_wrong": int(d_neither),
        "significant_0.05": bool(p_value < 0.05),
        "significant_0.01": bool(p_value < 0.01),
    }


def compute_metrics(
    samples: list[Sample],
    predictions: list[Prediction],
    label: str,
) -> dict:
    """Compute classification metrics for a single router config."""
    from sklearn.metrics import (
        accuracy_score,
        f1_score,
        classification_report,
        confusion_matrix,
    )

    n = len(samples)
    y_true_intent = [s.expected_intent for s in samples]
    y_pred_intent = [p.intent for p in predictions]
    y_true_scope = [s.expected_scope for s in samples]
    y_pred_scope = [p.scope for p in predictions]

    # Error count
    errors = sum(1 for p in predictions if p.error)
    parse_errors = sum(1 for p in predictions if p.error and "json_parse" in (p.error or ""))
    # Invalid intent count (hallucinated intents not in VALID_INTENTS)
    invalid_intents = sum(1 for p in predictions if p.intent and p.intent not in VALID_INTENTS)
    invalid_intent_names = sorted(set(
        p.intent for p in predictions if p.intent and p.intent not in VALID_INTENTS
    ))

    # Intent metrics
    intent_acc = accuracy_score(y_true_intent, y_pred_intent)
    intent_f1_macro = f1_score(y_true_intent, y_pred_intent, average="macro", zero_division=0)
    intent_f1_weighted = f1_score(y_true_intent, y_pred_intent, average="weighted", zero_division=0)

    # Per-intent classification report
    present_labels = sorted(set(y_true_intent + y_pred_intent) & set(VALID_INTENTS))
    intent_report = classification_report(
        y_true_intent, y_pred_intent,
        labels=present_labels,
        output_dict=True,
        zero_division=0,
    )

    # Scope metrics
    scope_acc = accuracy_score(y_true_scope, y_pred_scope)

    # Joint accuracy (intent + scope both correct)
    joint_correct = sum(
        1 for s, p in zip(samples, predictions)
        if s.expected_intent == p.intent and s.expected_scope == p.scope
    )
    joint_acc = joint_correct / n

    # Per-sample correctness (for McNemar later)
    intent_correct = [s.expected_intent == p.intent for s, p in zip(samples, predictions)]

    # Latency
    latencies = [p.latency_ms for p in predictions if p.error is None]
    latency_stats = {}
    if latencies:
        latency_stats = {
            "p50_ms": round(np.percentile(latencies, 50), 1),
            "p90_ms": round(np.percentile(latencies, 90), 1),
            "p95_ms": round(np.percentile(latencies, 95), 1),
            "mean_ms": round(np.mean(latencies), 1),
            "min_ms": round(np.min(latencies), 1),
            "max_ms": round(np.max(latencies), 1),
        }

    # Wilson CI
    ci_lo, ci_hi = wilson_ci(sum(intent_correct), n)

    # Confusion matrix
    cm = confusion_matrix(y_true_intent, y_pred_intent, labels=present_labels)

    return {
        "config": label,
        "total_samples": n,
        "errors": errors,
        "parse_errors": parse_errors,
        "invalid_intents": invalid_intents,
        "invalid_intent_names": invalid_intent_names,
        "intent_accuracy": round(intent_acc * 100, 2),
        "intent_accuracy_ci95": [round(ci_lo * 100, 2), round(ci_hi * 100, 2)],
        "intent_f1_macro": round(intent_f1_macro * 100, 2),
        "intent_f1_weighted": round(intent_f1_weighted * 100, 2),
        "scope_accuracy": round(scope_acc * 100, 2),
        "joint_accuracy": round(joint_acc * 100, 2),
        "latency": latency_stats,
        "per_intent_report": intent_report,
        "confusion_matrix": cm.tolist(),
        "confusion_labels": present_labels,
        "_intent_correct": intent_correct,  # for McNemar (not saved)
    }


# ═══════════════════════════════════════════════════════════════════
# Data loading
# ═══════════════════════════════════════════════════════════════════

def load_val_data(path: Path, limit: int | None = None) -> list[Sample]:
    """Load validation samples from JSONL."""
    samples = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if limit and i >= limit:
                break
            obj = json.loads(line.strip())
            samples.append(Sample(
                idx=i,
                input_text=obj["input"],
                context=obj.get("context"),
                expected_intent=obj["output"]["intent"],
                expected_scope=obj["output"]["scope"],
            ))
    logger.info("Loaded %d validation samples from %s", len(samples), path)
    return samples


# ═══════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════

def run_config(
    router,
    samples: list[Sample],
    label: str,
) -> list[Prediction]:
    """Run a router config on all samples with progress logging."""
    predictions = []
    total = len(samples)
    t0 = time.perf_counter()

    for i, sample in enumerate(samples):
        pred = router.predict(sample.input_text, sample.context)
        predictions.append(pred)

        # Progress every 50 samples
        if (i + 1) % 50 == 0 or (i + 1) == total:
            elapsed = time.perf_counter() - t0
            rate = (i + 1) / elapsed
            correct = sum(
                1 for s, p in zip(samples[:i+1], predictions)
                if s.expected_intent == p.intent
            )
            acc = correct / (i + 1) * 100
            logger.info(
                "[%s] %d/%d (%.1f/s) — running acc: %.1f%%",
                label, i + 1, total, rate, acc,
            )

    total_time = time.perf_counter() - t0
    logger.info("[%s] Done in %.1fs (avg %.1fms/query)", label, total_time, total_time / total * 1000)
    return predictions


# ═══════════════════════════════════════════════════════════════════
# Output
# ═══════════════════════════════════════════════════════════════════

def save_results(
    all_metrics: list[dict],
    all_predictions: dict[str, list[Prediction]],
    samples: list[Sample],
    mcnemar_results: dict,
    output_dir: Path,
):
    """Save all experiment results."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Summary JSON (main results)
    summary = {
        "experiment": "Exp1_Router_Comparison",
        "dataset": "multitask_val_v3.jsonl",
        "n_samples": len(samples),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "configs": [],
    }
    for m in all_metrics:
        config_summary = {k: v for k, v in m.items() if k != "_intent_correct"}
        summary["configs"].append(config_summary)
    summary["mcnemar_tests"] = mcnemar_results

    with open(output_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=_json_default)
    logger.info("Saved summary → %s", output_dir / "summary.json")

    # 2. Per-sample CSV (detailed predictions)
    import csv
    csv_path = output_dir / "predictions.csv"
    configs = list(all_predictions.keys())
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        header = ["idx", "input", "context", "expected_intent", "expected_scope"]
        for cfg in configs:
            header.extend([
                f"{cfg}_intent", f"{cfg}_scope", f"{cfg}_conf",
                f"{cfg}_latency_ms", f"{cfg}_correct",
            ])
        writer.writerow(header)

        for i, sample in enumerate(samples):
            row = [
                sample.idx,
                sample.input_text[:100],
                json.dumps(sample.context, ensure_ascii=False) if sample.context else "",
                sample.expected_intent,
                sample.expected_scope,
            ]
            for cfg in configs:
                pred = all_predictions[cfg][i]
                correct = sample.expected_intent == pred.intent
                row.extend([
                    pred.intent, pred.scope,
                    round(pred.confidence, 3),
                    round(pred.latency_ms, 1),
                    1 if correct else 0,
                ])
            writer.writerow(row)
    logger.info("Saved predictions → %s", csv_path)

    # 3. Comparison table (human-readable)
    table_path = output_dir / "comparison_table.txt"
    with open(table_path, "w", encoding="utf-8") as f:
        f.write("=" * 90 + "\n")
        f.write("Experiment 1: Router Comparison (RQ1)\n")
        f.write(f"Dataset: {len(samples)} samples from multitask_val_v3.jsonl\n")
        f.write("=" * 90 + "\n\n")

        # Header
        f.write(f"{'Config':<22} {'Intent Acc':>10} {'95% CI':>16} {'Macro-F1':>9} "
                f"{'Scope Acc':>10} {'Joint Acc':>10} {'P50 (ms)':>9} {'P90 (ms)':>9}\n")
        f.write("-" * 90 + "\n")

        for m in all_metrics:
            lat = m.get("latency", {})
            ci = m.get("intent_accuracy_ci95", [0, 0])
            f.write(
                f"{m['config']:<22} {m['intent_accuracy']:>9.1f}% "
                f"[{ci[0]:>5.1f}, {ci[1]:>5.1f}] "
                f"{m['intent_f1_macro']:>8.1f}% "
                f"{m['scope_accuracy']:>9.1f}% "
                f"{m['joint_accuracy']:>9.1f}% "
                f"{lat.get('p50_ms', 'N/A'):>9} "
                f"{lat.get('p90_ms', 'N/A'):>9}\n"
            )

        f.write("\n")

        # McNemar results
        if mcnemar_results:
            f.write("\nMcNemar's Test (paired comparison with R1):\n")
            f.write("-" * 70 + "\n")
            f.write(f"{'Pair':<30} {'chi2':>8} {'p-value':>10} {'Sig.(0.05)':>12}\n")
            f.write("-" * 70 + "\n")
            for pair, result in mcnemar_results.items():
                sig = "YES ***" if result.get("significant_0.01") else (
                    "YES *" if result.get("significant_0.05") else "no"
                )
                f.write(f"{pair:<30} {result['chi2']:>8.3f} {result['p_value']:>10.6f} {sig:>12}\n")

        f.write("\n")

        # Per-intent breakdown for each config
        for m in all_metrics:
            f.write(f"\n--- {m['config']} per-intent F1 ---\n")
            report = m.get("per_intent_report", {})
            f.write(f"{'Intent':<25} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Support':>10}\n")
            f.write("-" * 65 + "\n")
            for intent in sorted(VALID_INTENTS):
                if intent in report:
                    r = report[intent]
                    f.write(
                        f"{intent:<25} {r['precision']:>9.2f} {r['recall']:>9.2f} "
                        f"{r['f1-score']:>9.2f} {int(r['support']):>10}\n"
                    )
            f.write("\n")

    logger.info("Saved comparison table → %s", table_path)

    # 4. Confusion matrices (one JSON per config)
    for m in all_metrics:
        cm_path = output_dir / f"confusion_{m['config'].lower().replace(' ', '_').replace('.', '')}.json"
        with open(cm_path, "w", encoding="utf-8") as f:
            json.dump({
                "config": m["config"],
                "labels": m["confusion_labels"],
                "matrix": m["confusion_matrix"],
            }, f, indent=2, ensure_ascii=False, default=_json_default)


def _elapsed_ms(t0: float) -> float:
    return (time.perf_counter() - t0) * 1000


def _json_default(obj):
    """Convert numpy scalar types to Python native for JSON serialization."""
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Exp 1: Router Comparison")
    parser.add_argument(
        "--configs", nargs="+", default=["R1", "R2", "R3", "R4"],
        help="Which configs to run (default: all)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Only run 5 samples per config",
    )
    parser.add_argument(
        "--skip-scope", action="store_true",
        help="Skip scope accuracy (focus on intent only)",
    )
    parser.add_argument(
        "--val-path", type=str,
        default=str(ROOT / "data" / "router" / "multitask_val_v3.jsonl"),
        help="Path to validation JSONL",
    )
    parser.add_argument(
        "--output-dir", type=str, default=str(OUTPUT_DIR),
        help="Output directory",
    )
    args = parser.parse_args()

    # Load data
    limit = 5 if args.dry_run else None
    samples = load_val_data(Path(args.val_path), limit=limit)

    # Build routers
    routers: dict[str, Any] = {}
    config_descriptions = {
        "R1": f"R1. Qwen3-4B FT (Ollama: {OLLAMA_FT_MODEL})",
        "R2": f"R2. Qwen3-4B ZS API ({QWEN3_4B_MODEL})",
        "R3": f"R3. GPT-4o-mini ZS ({GPT4O_MINI_MODEL})",
        "R4": f"R4. GPT-4o ZS ({GPT4O_MODEL})",
    }

    for cfg in args.configs:
        cfg = cfg.upper()
        if cfg == "R1":
            routers[cfg] = OllamaRouter(model=OLLAMA_FT_MODEL, label="R1. Qwen3-4B FT")
        elif cfg == "R2":
            if not QWEN3_4B_API_KEY or not QWEN3_4B_API_BASE:
                logger.warning("Skipping R2: QWEN3_4B_API_KEY / QWEN3_4B_API_BASE not set in .env")
                continue
            routers[cfg] = OpenAIRouter(
                api_key=QWEN3_4B_API_KEY,
                api_base=QWEN3_4B_API_BASE,
                model=QWEN3_4B_MODEL,
                label="R2. Qwen3-4B ZS API",
            )
        elif cfg == "R3":
            if not GPT4O_MINI_API_KEY:
                logger.warning("Skipping R3: JUDGE_API_KEY not set")
                continue
            routers[cfg] = OpenAIRouter(
                api_key=GPT4O_MINI_API_KEY,
                api_base=GPT4O_MINI_API_BASE,
                model=GPT4O_MINI_MODEL,
                label="R3. GPT-4o-mini ZS",
            )
        elif cfg == "R4":
            if not GPT4O_API_KEY:
                logger.warning("Skipping R4: GPT4O_API_KEY not set")
                continue
            routers[cfg] = OpenAIRouter(
                api_key=GPT4O_API_KEY,
                api_base=GPT4O_API_BASE,
                model=GPT4O_MODEL,
                label="R4. GPT-4o ZS",
            )
        else:
            logger.warning("Unknown config: %s (valid: R1, R2, R3, R4)", cfg)

    if not routers:
        logger.error("No valid router configs to run!")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("Experiment 1: Router Comparison")
    logger.info("Configs: %s", list(routers.keys()))
    logger.info("Samples: %d%s", len(samples), " (dry run)" if args.dry_run else "")
    logger.info("=" * 60)

    # Run each config
    all_predictions: dict[str, list[Prediction]] = {}
    all_metrics: list[dict] = []

    for cfg_name, router in routers.items():
        logger.info("\n>>> Running %s: %s", cfg_name, config_descriptions.get(cfg_name, ""))
        predictions = run_config(router, samples, cfg_name)
        all_predictions[cfg_name] = predictions

        metrics = compute_metrics(samples, predictions, config_descriptions.get(cfg_name, cfg_name))
        all_metrics.append(metrics)

        # Print quick summary
        logger.info(
            "[%s] Intent Acc: %.1f%% [%.1f, %.1f] | Macro-F1: %.1f%% | Scope: %.1f%%",
            cfg_name,
            metrics["intent_accuracy"],
            metrics["intent_accuracy_ci95"][0],
            metrics["intent_accuracy_ci95"][1],
            metrics["intent_f1_macro"],
            metrics["scope_accuracy"],
        )

        # Cleanup
        if hasattr(router, "close"):
            router.close()

    # McNemar paired comparisons (R1 vs each other)
    mcnemar_results = {}
    r1_correct = None
    for m in all_metrics:
        if m["config"].startswith("R1"):
            r1_correct = m["_intent_correct"]
            break

    if r1_correct and len(all_metrics) > 1:
        for m in all_metrics:
            if m["config"].startswith("R1"):
                continue
            pair_name = f"R1 vs {m['config'][:2]}"
            try:
                result = mcnemar_test(r1_correct, m["_intent_correct"])
                mcnemar_results[pair_name] = result
                sig = " ***" if result["significant_0.01"] else (" *" if result["significant_0.05"] else "")
                logger.info(
                    "McNemar %s: chi2=%.3f, p=%.6f%s",
                    pair_name, result["chi2"], result["p_value"], sig,
                )
            except Exception as e:
                logger.warning("McNemar %s failed: %s", pair_name, e)

    # Save results
    output_dir = Path(args.output_dir)
    save_results(all_metrics, all_predictions, samples, mcnemar_results, output_dir)

    # Final summary
    print("\n" + "=" * 70)
    print("EXPERIMENT 1 — ROUTER COMPARISON — RESULTS")
    print("=" * 70)
    print(f"{'Config':<25} {'Intent Acc':>11} {'Macro-F1':>10} {'Scope Acc':>11}")
    print("-" * 60)
    for m in all_metrics:
        print(f"{m['config']:<25} {m['intent_accuracy']:>10.1f}% {m['intent_f1_macro']:>9.1f}% {m['scope_accuracy']:>10.1f}%")
    print("-" * 60)
    print(f"\nResults saved to: {output_dir}")


if __name__ == "__main__":
    main()
