import json
import sys
from collections import defaultdict
sys.path.insert(0, "analysis/round1/profile")
from extract import load, repo_of

OUT = "analysis/round1/profile/out"
recs = {r["case_code"]: r for r in load("canonical")}
ents = json.load(open(f"{OUT}/entities_canonical.json"))
pairs = json.load(open(f"{OUT}/pairs_all.json"))
adj = defaultdict(set)
for kind, a, b in pairs:
    adj[a].add((kind, b))
    adj[b].add((kind, a))
weak = {"미상", "추론"}


def show(code):
    r = recs[code]
    return f"{code} [{r['cause_basis']}/{r['cause_class'] or '-'}] {r['title'][:90]}"


print("## A. weak-cause record -> 1 hop -> 명시 record, different cause_class or different title domain")
n = 0
for a in sorted(adj):
    if recs[a]["cause_basis"] not in weak:
        continue
    for kind, b in sorted(adj[a]):
        if recs[b]["cause_basis"] == "명시" and kind in {"xref", "err_specific", "func"}:
            print(f"[{kind}] {show(a)}\n      -> {show(b)}")
            n += 1
            break
    if n >= 25:
        break

print("\n## B. 2-hop chains a -(xref)- b -(mr/commit/err/func)- c, all distinct repos-same, c 명시, a weak")
n = 0
for a in sorted(adj):
    if recs[a]["cause_basis"] not in weak:
        continue
    for k1, b in adj[a]:
        if k1 != "xref":
            continue
        for k2, c in adj[b]:
            if c in (a,) or k2 == "xref" or recs[c]["cause_basis"] != "명시":
                continue
            if any(x == c for _, x in adj[a]):
                continue
            print(f"{show(a)}\n   -[{k1}]-> {show(b)}\n   -[{k2}]-> {show(c)}")
            n += 1
            break
        else:
            continue
        break
    if n >= 15:
        break

print("\n## C. shared specific error signature across different SW versions/cause_class")
sig_groups = defaultdict(set)
for code, e in ents.items():
    for s in e["err_specific"]:
        sig_groups[(repo_of(recs[code]["source_id"]), s)].add(code)
for (repo, sig), codes in sorted(sig_groups.items(), key=lambda kv: -len(kv[1])):
    if not 3 <= len(codes) <= 12:
        continue
    classes = {recs[c]["cause_class"] for c in codes if recs[c]["cause_class"]}
    if len(classes) >= 2:
        print(f"{repo} {sig[:90]} n={len(codes)} classes={classes}")
        for c in sorted(codes):
            print(f"     {show(c)} ver={ents[c]['version'][:3]}")

print("\n## D. one MR/PR closing several issues with different symptoms")
mr_groups = defaultdict(set)
for code, e in ents.items():
    for m in e["ref_mr_pr"]:
        mr_groups[(repo_of(recs[code]["source_id"]), m)].add(code)
for (repo, m), codes in sorted(mr_groups.items(), key=lambda kv: -len(kv[1])):
    if 3 <= len(codes) <= 8 and repo != "launchpad:neutron":
        eqs = {recs[c]["equipment"] for c in codes}
        print(f"{repo} PR/MR {m} n={len(codes)} equipment={eqs}")
        for c in sorted(codes):
            print(f"     {show(c)}")
