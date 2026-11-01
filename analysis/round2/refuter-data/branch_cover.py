import sys, json, collections
sys.path.insert(0, sys.argv[1])
import slot_sim as S
def weights(top):
    w = collections.Counter()
    for c in top:
        vals = S.DOC_VALUES[c]["repo"] or {"<none>"}
        for v in vals: w[v] += 1.0/len(vals)
    return w
def grouped(ranking, repos, per):
    out = []
    for r in repos: out += [c for c in ranking if r in S.DOC_VALUES[c]["repo"]][:per]
    return out
hit = lambda shown, g: int(any(c in g for c in shown))
st = collections.defaultdict(collections.Counter)
for line in open(sys.argv[2]):
    r = json.loads(line)
    if r["slots"]["repo"]["present"]: continue
    g = set(r["golds"]); ranking = [c for c in S.search(r["q"]) if c != r["case"]]
    w = weights(ranking[:20]); tot = sum(w.values()); mc = w.most_common(3)
    if mc[0][1]/tot >= 0.7: continue
    cov3 = sum(v for _, v in mc)/tot
    key = "cov3>=0.8" if cov3 >= 0.8 else "cov3<0.8"
    s = st[key]; s["n"] += 1
    s["top6"] += hit(ranking[:6], g)
    s["branch3x2"] += hit(grouped(ranking, [k for k, _ in mc], 2), g)
    s["branch2x3"] += hit(grouped(ranking, [k for k, _ in mc[:2]], 3), g)
    gold_repo = {S.repo_of(S.C[r["case"]]["source_id"])}
    s["gold_repo_in_top3"] += int(bool(gold_repo & {k for k, _ in mc}))
for k, s in st.items():
    n = s["n"]; print(k, "n=", n, {x: round(s[x]/n, 3) for x in s if x != "n"})
