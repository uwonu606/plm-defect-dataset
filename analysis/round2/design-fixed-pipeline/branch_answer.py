import sys, json, collections, os
CLARIFY = "analysis/round2/clarify-slots"
sys.path.insert(0, CLARIFY)
import slot_sim as S

RESULTS = sys.argv[1] if len(sys.argv) > 1 else CLARIFY + "/results_neighbor_all.jsonl"
TAU = float(os.environ.get("TAU", "0.7"))


def repo_weights(top):
    w = collections.Counter()
    for c in top:
        vals = S.DOC_VALUES[c]["repo"] or {"<none>"}
        for v in vals:
            w[v] += 1.0 / len(vals)
    return w


def grouped(ranking, repos, per_repo):
    shown = []
    for repo in repos:
        shown += [c for c in ranking if repo in S.DOC_VALUES[c]["repo"]][:per_repo]
    return shown


def hit(shown, golds):
    return int(any(c in golds for c in shown))


stats = collections.defaultdict(lambda: collections.Counter())
for line in open(RESULTS, encoding="utf-8"):
    r = json.loads(line)
    if r["slots"]["repo"]["present"]:
        continue
    golds = set(r["golds"])
    ranking = [c for c in S.search(r["q"]) if c != r["case"]]
    top20 = ranking[:20]
    w = repo_weights(top20)
    max_share = w.most_common(1)[0][1] / sum(w.values())
    fired = max_share < TAU
    gold_repo = {S.repo_of(S.C[r["case"]]["source_id"])}
    in_repo = [c for c in ranking if S.DOC_VALUES[c]["repo"] & gold_repo]
    row = {
        "top5": hit(ranking[:5], golds),
        "top6": hit(ranking[:6], golds),
        "ask_filter5": hit(in_repo[:5], golds),
        "branch2x3": hit(grouped(ranking, [v for v, _ in w.most_common(2)], 3), golds),
        "branch3x2": hit(grouped(ranking, [v for v, _ in w.most_common(3)], 2), golds),
        "gold_repo_in_top2": int(bool(gold_repo & {v for v, _ in w.most_common(2)})),
    }
    for key in (r["qtype"], "all"):
        s = stats[(key, "fired" if fired else "not_fired")]
        s["n"] += 1
        for k, v in row.items():
            s[k] += v

for (key, part), s in sorted(stats.items()):
    n = s["n"]
    print(f"{key:9s} {part:10s} n={n:4d} " + " ".join(f"{k}={s[k]/n:.3f}" for k in
          ("top5", "top6", "ask_filter5", "branch2x3", "branch3x2", "gold_repo_in_top2")))

for key in ("title", "problem1", "short6", "all"):
    f, nf = stats[(key, "fired")], stats[(key, "not_fired")]
    n = f["n"] + nf["n"]
    print(f"POLICY {key:9s} n={n} fired={f['n']/n:.3f} "
          f"never_ask_top5={(f['top5']+nf['top5'])/n:.3f} never_ask_top6={(f['top6']+nf['top6'])/n:.3f} "
          f"ask_filter={(f['ask_filter5']+nf['top5'])/n:.3f} "
          f"branch2x3={(f['branch2x3']+nf['top6'])/n:.3f} branch3x2={(f['branch3x2']+nf['top6'])/n:.3f}")
