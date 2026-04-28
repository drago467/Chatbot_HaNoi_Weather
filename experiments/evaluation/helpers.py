"""Helper functions for evaluation — extract tool info, load data."""
import csv
import json


def extract_tool_names(result) -> list:
    """Extract tool names called from agent result messages."""
    tools = []
    for msg in result.get("messages", []):
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
                if name:
                    tools.append(name)
    return tools


def extract_tool_outputs(result) -> str:
    """Extract tool outputs from agent result for faithfulness check.

    PR-C.5 (2026-04-27): bỏ `[:4000]` per-tool truncation. Bug cũ: judge
    faithfulness mất context khi tool_outputs > 4K chars (vd hourly 48h ×
    10 fields). Feed full vào judge ở `judges.py` / `backends/judge.py`.
    Caller cần CSV cap nên tự `[:N]` ở storage layer (vd runner.py:83).
    """
    outputs = []
    for msg in result.get("messages", []):
        msg_type = getattr(msg, "type", None)
        if msg_type == "tool":
            content = getattr(msg, "content", str(msg))
            if content:
                outputs.append(str(content))
    return "\n---\n".join(outputs) if outputs else ""


def extract_detailed_tool_calls(result) -> list:
    """Extract detailed tool calls with name, input, output from agent result.

    Pairs AIMessage.tool_calls with ToolMessage responses via tool_call_id.
    Returns list of dicts: [{name, input, output}, ...]
    """
    messages = result.get("messages", [])

    # Map tool_call_id → output content
    tool_outputs = {}
    for msg in messages:
        if getattr(msg, "type", None) == "tool":
            tc_id = getattr(msg, "tool_call_id", "")
            content = getattr(msg, "content", "")
            if tc_id:
                tool_outputs[tc_id] = str(content)[:500]

    calls = []
    for msg in messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                if isinstance(tc, dict):
                    name = tc.get("name")
                    args = tc.get("args", {})
                    tc_id = tc.get("id", "")
                else:
                    name = getattr(tc, "name", None)
                    args = getattr(tc, "args", {})
                    tc_id = getattr(tc, "id", "")
                if name:
                    calls.append({
                        "name": name,
                        "input": str(args)[:200],
                        "output": tool_outputs.get(tc_id, ""),
                    })
    return calls


def categorize_error(error_str: str) -> str:
    """Categorize error type for analysis."""
    err = error_str.lower()
    if "location" in err or "not_found" in err or "ambiguous" in err:
        return "location_resolution"
    elif "no_data" in err or "database" in err or "không có dữ liệu" in err:
        return "data_unavailable"
    elif "timeout" in err or "connection" in err or "refused" in err:
        return "network"
    elif "openai" in err or "api" in err or "rate_limit" in err:
        return "llm_api"
    return "unknown"


def load_test_queries(csv_path):
    """Load test queries from evaluation CSV file."""
    queries = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            queries.append(row)
    return queries


def load_jsonl(path: str) -> list:
    """Load a JSONL file, one JSON object per line."""
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items
