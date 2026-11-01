import sys, json, re, collections
src = open(sys.argv[1]).read()
# take module header up to BM25 section (no search); exec definitions only
head = src.split("# ---------- BM25 ----------")[0]
g = {"__name__": "x", "__file__": sys.argv[1]}
exec(compile(head, "slot_sim_head", "exec"), g)
DV = g["DOC_VALUES"]
res = [json.loads(l) for l in open(sys.argv[2])]
cnt = collections.Counter()
for r in res:
    s = r["slots"]["version"]
    if not s["present"] or not s["gold_vals"]:
        continue
    gv = set(s["gold_vals"])
    for gcase in r["golds"]:
        nv = DV[gcase]["version"]
        if not nv: cnt[(r["qtype"], "neighbor_no_version")] += 1
        elif nv & gv: cnt[(r["qtype"], "match")] += 1
        else: cnt[(r["qtype"], "differs")] += 1
for k in sorted(cnt): print(k, cnt[k])
# pair-level over all dup/xref pairs
pairs = json.load(open(g["PROFILE"] + "/out/pairs_all.json"))
pc = collections.Counter()
for kind, a, b in pairs:
    if kind not in ("dup", "xref"): continue
    va, vb = DV[a]["version"], DV[b]["version"]
    if not va or not vb: pc["one_or_both_missing"] += 1
    elif va & vb: pc["share_majmin"] += 1
    else: pc["disjoint_majmin"] += 1
print("pairs", dict(pc))
