"""Push router train/val + system prompt lên HF dataset repo.

Usage:
    $env:HF_TOKEN = "hf_..."          # PowerShell
    export HF_TOKEN=hf_...             # bash
    python scripts/router/upload_router_data_hf.py
"""
import os
import sys
from pathlib import Path

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parents[2]
HF_REPO_ID = "daredevil467/hanoi-weather-router-data-v7"

FILES_TO_UPLOAD = {
    "multitask_train.jsonl": ROOT / "data/router/multitask_train.jsonl",
    "multitask_val.jsonl":   ROOT / "data/router/multitask_val.jsonl",
    "system_prompt.txt":     ROOT / "data/router/system_prompt.txt",
}


def main() -> None:
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("ERROR: HF_TOKEN env var not set.", file=sys.stderr)
        sys.exit(1)

    for name, path in FILES_TO_UPLOAD.items():
        if not path.exists():
            print(f"ERROR: Missing {path}", file=sys.stderr)
            sys.exit(1)

    api = HfApi(token=token)

    print(f"Pushing to: {HF_REPO_ID}")
    for name, path in FILES_TO_UPLOAD.items():
        print(f"  Uploading {name} ({path.stat().st_size} bytes)...")
        api.upload_file(
            path_or_fileobj=str(path),
            path_in_repo=name,
            repo_id=HF_REPO_ID,
            repo_type="dataset",
        )

    print(f"\nDone. Dataset: https://huggingface.co/datasets/{HF_REPO_ID}")


if __name__ == "__main__":
    main()
