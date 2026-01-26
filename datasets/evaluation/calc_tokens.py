import sys
import os
import json
import re
from typing import Iterable, List, Dict, Any
from statistics import mean, median, pstdev

JSON_RE = re.compile(r"\{.*\}")

def iter_json_objects_from_file(path: str) -> Iterable[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # try direct json
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    yield obj
                    continue
            except Exception:
                pass
            # try to extract first JSON object substring
            m = JSON_RE.search(line)
            if m:
                try:
                    obj = json.loads(m.group(0))
                    if isinstance(obj, dict):
                        yield obj
                except Exception:
                    continue

def extract_token_fields(item: Dict[str, Any]) -> Dict[str, int]:
    # common keys used by agent logs
    keys = ["prompt_tokens", "completion_tokens", "total_tokens", "meta", "tokens"]
    out = {"prompt_tokens": None, "completion_tokens": None, "total_tokens": None}
    for k in out.keys():
        if k in item and isinstance(item[k], int):
            out[k] = item[k]
    # sometimes nested under meta or different names
    if out["total_tokens"] is None:
        for alt in ("total_tokens", "total", "tokens"):
            if alt in item and isinstance(item[alt], int):
                out["total_tokens"] = item[alt]
                break
    if out["prompt_tokens"] is None:
        if "prompt" in item and isinstance(item["prompt"], dict):
            if "tokens" in item["prompt"] and isinstance(item["prompt"]["tokens"], int):
                out["prompt_tokens"] = item["prompt"]["tokens"]
    # fallback to meta
    meta = item.get("meta") or item.get("metrics") or {}
    if isinstance(meta, dict):
        for k in ("prompt_tokens", "completion_tokens", "total_tokens"):
            if out.get(k) is None and isinstance(meta.get(k), int):
                out[k] = meta.get(k)
    # compute missing total if prompt+completion present
    if out["total_tokens"] is None and out["prompt_tokens"] is not None and out["completion_tokens"] is not None:
        out["total_tokens"] = out["prompt_tokens"] + out["completion_tokens"]
    # ensure integers or None
    for k in out:
        if not isinstance(out[k], int):
            out[k] = None
    return out

def summarize_token_list(values: List[int]) -> Dict[str, Any]:
    if not values:
        return {"sum": 0, "avg": 0, "min": None, "max": None}
    return {
        "sum": sum(values),
        "avg": mean(values),
        "min": min(values),
        "max": max(values)
    }

def summarize(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    prompts, comps, totals = [], [], []
    for it in items:
        toks = extract_token_fields(it)
        if toks["prompt_tokens"] is not None:
            prompts.append(toks["prompt_tokens"])
        if toks["completion_tokens"] is not None:
            comps.append(toks["completion_tokens"])
        if toks["total_tokens"] is not None:
            totals.append(toks["total_tokens"])
    return {
        "prompt": summarize_token_list(prompts),
        "completion": summarize_token_list(comps),
        "total": summarize_token_list(totals),
    }

# compute time cost
def compute_stage_elapsed(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    stages = ["arch", "skeleton", "code"]
    result: Dict[str, Any] = {s: {"total_seconds": 0.0, "count": 0} for s in stages}
    total_all = 0.0

    for rec in items:
        meta = rec.get("meta") or {}
        node_val = ""
        elapsed = rec.get("elapsed_seconds")
        if isinstance(meta, dict):
            node_val = str(meta.get("langgraph_node") or meta.get("node") or "")
        else:
            node_val = str(meta)
        node_lower = node_val.lower()
        matched = False
        for s in stages:
            if s.lower() in node_lower:
                try:
                    result[s]["total_seconds"] += float(elapsed)
                    result[s]["count"] += 1
                except Exception:
                    # skip records with non-numeric elapsed
                    continue
                matched = True
        if matched:
            try:
                total_all += float(elapsed)
            except Exception:
                pass

    result["total_all"] = total_all
    return result


if __name__ == "__main__":
    log_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'DevBench_outputs/gpt-4o/agent_metrics.log')
    items = iter_json_objects_from_file(log_file)
    summary = summarize(items)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    time = compute_stage_elapsed(items)
    print(json.dumps(time, ensure_ascii=False, indent=2))