import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import engine as e
import run as R
import systems as s


def without(intent):
    def normalize_fn(question):
        slots, hint, intents = s.normalize(question)
        return slots, hint, intents - {intent}
    return normalize_fn


def no_identifier(item, tau):
    original = e.find_by_identifier
    e.find_by_identifier = lambda text, max_df=10: []
    try:
        return s.fixed_dag(item, tau)
    finally:
        e.find_by_identifier = original


def tool_counts(results_name):
    counts = collections.defaultdict(list)
    items = {it["qid"]: it for it in R.load()}
    for out in map(json.loads, open(e.results_dir() / f"{results_name}.jsonl", encoding="utf-8")):
        n = sum(1 for t in out.get("trace", []) if "tool" in t)
        counts[items[out["qid"]]["type"]].append(n)
    return {k: round(sum(v) / len(v), 2) for k, v in sorted(counts.items())} | {
        "ALL": round(sum(sum(v) for v in counts.values()) / sum(len(v) for v in counts.values()), 2)}


def main():
    items = R.load()
    tau, _ = R.calibrate_tau(items)
    test = [it for it in items if it["split"] == "test" and it["type"] != "clarify"]
    variants = {"dag": lambda it, t: s.fixed_dag(it, t),
                "dag_no_expand": lambda it, t: s.fixed_dag(it, t, normalize_fn=without("cause")),
                "dag_no_identifier": no_identifier}
    out = {"tau_sweep": {}, "components": {}}
    for factor in (0, 0.5, 0.75, 1.0, 1.25):
        t = tau * factor
        rows = [R.score(it, s.fixed_dag(it, t)) for it in test]
        summary = R.summarize(rows)
        out["tau_sweep"][f"{factor:.2f}xtau={t:.1f}"] = {k: summary[k]["success"] for k in summary}
    for name, fn in variants.items():
        rows = [R.score(it, fn(it, tau)) for it in test]
        summary = R.summarize(rows)
        out["components"][name] = {k: summary[k]["success"] for k in summary}
    out["tool_calls_per_question"] = {name: tool_counts(name) for name in ("dag_regex", "dag_llm_front", "llm_loop", "llm_planner")
                                      if (e.results_dir() / f"{name}.jsonl").exists()}
    (e.results_dir() / "ablations.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
