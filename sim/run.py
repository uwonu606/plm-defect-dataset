import collections
import json
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import engine as e
import systems as s

RESULTS = HERE / "results"
RETRIEVAL_TYPES = ("single", "logpaste", "multihop", "fix", "composite")
TRUE_INTENTS = {"single": set(), "logpaste": {"cause"}, "multihop": {"cause"}, "fix": {"fix"},
                "composite": {"cause", "fix"}, "aggregate": {"aggregate"}, "clarify": set()}


def load():
    return [json.loads(line) for line in open(HERE / "testset.jsonl", encoding="utf-8")]


def calibrate_tau(items):
    answerable = [e.search(it["question"], k=1) for it in items if it["split"] == "dev" and it["type"] in RETRIEVAL_TYPES]
    unanswerable = [e.search(it["question"], k=1) for it in items if it["split"] == "dev" and it["type"] == "unanswerable"]
    pos = [h[0]["score"] if h else 0 for h in answerable]
    neg = [h[0]["score"] if h else 0 for h in unanswerable]
    best = max(sorted(set(pos + neg)), key=lambda t: (sum(x >= t for x in pos) / len(pos) + sum(x < t for x in neg) / len(neg)))
    return best, {"dev_answerable": len(pos), "dev_unanswerable": len(neg)}


def score(item, out):
    gold = set(item.get("gold_cases") or [])
    cases = out.get("cases") or []
    row = {"qid": item["qid"], "type": item["type"], "abstain": out.get("abstain", False)}
    if item["type"] in RETRIEVAL_TYPES:
        ranks = [i for i, c in enumerate(cases[:10]) if c in gold]
        row["hit5"] = bool(ranks and ranks[0] < 5) and not row["abstain"]
        row["recall10"] = len(gold & set(cases[:10])) / len(gold) if not row["abstain"] else 0.0
        row["mrr"] = 1 / (ranks[0] + 1) if ranks and not row["abstain"] else 0.0
    if item["type"] in ("fix", "composite"):
        row["status_ok"] = out.get("fix_status") == item["gold_status"]
    if item["type"] == "aggregate":
        row["count_ok"] = out.get("count") == item["gold_count"]
    success = {
        "single": row.get("hit5"), "logpaste": row.get("hit5"),
        "multihop": row.get("recall10", 0) > 0, "fix": row.get("status_ok"),
        "composite": row.get("hit5") and row.get("status_ok"), "aggregate": row.get("count_ok"),
        "unanswerable": row["abstain"],
    }
    row["success"] = bool(success[item["type"]])
    row["llm_calls"] = out.get("llm_calls", 0)
    row["llm_seconds"] = out.get("llm_seconds", 0)
    return row


def summarize(rows):
    by_type = collections.defaultdict(list)
    for r in rows:
        by_type[r["type"]].append(r)
    out = {}
    for kind, group in sorted(by_type.items()):
        stats = {"n": len(group), "success": mean(r["success"] for r in group)}
        for key in ("hit5", "recall10", "mrr", "status_ok", "count_ok"):
            values = [r[key] for r in group if key in r]
            if values:
                stats[key] = mean(values)
        if kind in RETRIEVAL_TYPES:
            stats["false_abstain"] = mean(r["abstain"] for r in group)
        out[kind] = stats
    out["ALL"] = {"n": len(rows), "success": mean(r["success"] for r in rows),
                  "llm_calls": mean(r["llm_calls"] for r in rows), "llm_seconds": mean(r["llm_seconds"] for r in rows)}
    return out


def mean(values):
    values = [float(v) for v in values]
    return round(sum(values) / len(values), 3) if values else None


def paired_bootstrap(a_rows, b_rows, key="success", n=4000, seed=7):
    pairs = {r["qid"]: [float(r[key])] for r in a_rows}
    for r in b_rows:
        pairs[r["qid"]].append(float(r[key]))
    diffs = [b - a for a, b in pairs.values()]
    rng = random.Random(seed)
    boots = sorted(sum(rng.choice(diffs) for _ in diffs) / len(diffs) for _ in range(n))
    return {"diff": round(sum(diffs) / len(diffs), 3), "ci95": [round(boots[int(n * .025)], 3), round(boots[int(n * .975)], 3)]}


def run_system(name, fn, items, workers=1):
    with ThreadPoolExecutor(workers) as pool:
        outs = list(pool.map(lambda it: s.timed(fn, it), items))
    with (RESULTS / f"{name}.jsonl").open("w", encoding="utf-8") as f:
        for it, out in zip(items, outs):
            f.write(json.dumps({"qid": it["qid"], **out}, ensure_ascii=False, default=list) + "\n")
    return [score(it, out) for it, out in zip(items, outs)]


def slot_accuracy(items, regex_fn, llm_table):
    rows = {"regex": collections.Counter(), "llm": collections.Counter()}
    n = collections.Counter()
    for it in items:
        if it["type"] not in TRUE_INTENTS:
            continue
        truth_product = e.product_of(e.corpus().canonical[it["seed"]]) if it.get("with_product") else None
        if it["type"] == "aggregate":
            truth_product = it["gold_filters"].get("product")
        for name, fn in (("regex", regex_fn), ("llm", s.llm_normalizer(llm_table))):
            slots, _, intents = fn(it["question"])
            rows[name]["intent_exact"] += intents == TRUE_INTENTS[it["type"]]
            rows[name]["product_exact"] += slots["product"] == truth_product
            if it["type"] == "aggregate":
                got = {k: v for k, v in slots.items() if v}
                rows[name]["aggregate_filters_exact"] += got == {k: str(v) for k, v in it["gold_filters"].items()}
        n["all"] += 1
        n["aggregate"] += it["type"] == "aggregate"
    return {name: {k: round(v / (n["aggregate"] if k.startswith("aggregate") else n["all"]), 3) for k, v in c.items()}
            for name, c in rows.items()} | {"n": dict(n)}


PERSONAS = ("cooperative", "unknown", "ignore", "wrong")
POLICIES = ("none", "endline", "endline_soft", "blocking", "ask_all")


def persona_reply(persona, truth, slot):
    if persona == "cooperative":
        return truth[slot]
    if persona == "wrong":
        pool = e.PRODUCTS if slot == "product" else e.EQUIPMENTS
        return pool[(pool.index(truth[slot]) + 3) % len(pool)]
    return None


def clarify_episode(item, policy, persona, share_tau, abstain_tau):
    q, gold = item["question"], set(item["gold_cases"])
    slots, hint, _ = s.normalize(q)
    first = e.search(q, filters={"product": slots["product"]} if slots["product"] else None, k=20, boost={"equipment": hint})
    products = collections.Counter(e.product_of(e.corpus().by_code[h["case_code"]]) for h in first)
    share = products.most_common(1)[0][1] / len(first) if first else 0
    ambiguous = slots["product"] is None and share < share_tau
    hit = lambda hits: any(h["case_code"] in gold for h in hits[:5])

    if policy == "none" or (policy != "ask_all" and not ambiguous):
        return {"asked": False, "turn1_hit5": hit(first), "final_hit5": hit(first), "turns": 1}
    blocking = policy in ("blocking", "ask_all")
    asked_slots = ["product"] + (["equipment"] if policy == "ask_all" else [])
    values = {slot: persona_reply(persona, item["slots"], slot) for slot in asked_slots}
    values = {k: v for k, v in values.items() if v}
    turn1 = [] if blocking else first
    if not values:
        return {"asked": True, "turn1_hit5": hit(turn1), "final_hit5": hit(first), "turns": 2 if blocking else 1}
    if policy == "endline_soft":
        second = e.search(q, k=20, boost={"product": values.get("product"), "equipment": hint})
    else:
        second = e.search(q, filters=values, k=20, boost={"equipment": hint})
        if not second or second[0]["score"] < abstain_tau:
            seen = {h["case_code"] for h in second}
            second = second[:5] + [h for h in first if h["case_code"] not in seen][:5]
    return {"asked": True, "turn1_hit5": hit(turn1), "final_hit5": hit(second), "turns": 2}


def clarify_sim(items, abstain_tau):
    group = [it for it in items if it["type"] == "clarify"]
    table = {}
    for share_tau in (0.5, 0.7):
        for policy in POLICIES:
            for persona in PERSONAS:
                eps = [clarify_episode(it, policy, persona, share_tau, abstain_tau) for it in group]
                table[f"tau{share_tau}/{policy}/{persona}"] = {
                    "ask_rate": mean(x["asked"] for x in eps), "turn1_hit5": mean(x["turn1_hit5"] for x in eps),
                    "final_hit5": mean(x["final_hit5"] for x in eps), "mean_turns": mean(x["turns"] for x in eps)}
    return {"n": len(group), "table": table}


def main():
    RESULTS.mkdir(exist_ok=True)
    items = load()
    tau, tau_info = calibrate_tau(items)
    test = [it for it in items if it["split"] == "test" and it["type"] != "clarify"]
    print(f"tau={tau:.2f} {tau_info}, test items={len(test)}", flush=True)

    llm_table, slot_seconds = {}, 0
    slot_items = [it for it in items if it["split"] == "test"]
    for i in range(0, len(slot_items), 15):
        part, sec = s.llm_slot_batch(slot_items[i:i + 15])
        slot_seconds += sec
        for it in slot_items[i:i + 15]:
            llm_table[it["question"]] = part.get(it["qid"], {})

    runs = {
        "bm25_only": lambda it: s.bm25_only(it, tau),
        "dag_regex": lambda it: s.fixed_dag(it, tau),
        "dag_llm_slots": lambda it: s.fixed_dag(it, tau, normalize_fn=s.llm_normalizer(llm_table)),
        "dag_llm_front": lambda it: s.dag_llm_front(it, tau),
        "llm_loop": lambda it: s.llm_loop(it, tau),
        "llm_planner": lambda it: s.llm_planner(it, tau),
    }
    rows = {}
    for name, fn in runs.items():
        rows[name] = run_system(name, fn, test, workers=6 if "llm" in name else 1)
        print(name, summarize(rows[name])["ALL"], flush=True)

    summary = {
        "tau": round(tau, 3), "tau_calibration": tau_info, "n_test": len(test),
        "systems": {name: summarize(r) for name, r in rows.items()},
        "paired_vs_dag_regex": {name: paired_bootstrap(rows["dag_regex"], r) for name, r in rows.items() if name != "dag_regex"},
        "slot_detection": slot_accuracy(slot_items, s.normalize, llm_table) | {"llm_seconds_total": round(slot_seconds, 1)},
        "clarify": clarify_sim(items, tau),
    }
    (RESULTS / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    print(json.dumps(summary["paired_vs_dag_regex"], ensure_ascii=False))


if __name__ == "__main__":
    main()
