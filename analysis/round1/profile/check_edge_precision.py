import json
import random
import sys
from collections import defaultdict
sys.path.insert(0, "analysis/round1/profile")
from extract import load, repo_of

OUT = "analysis/round1/profile/out"
recs = {r["case_code"]: r for r in load("canonical")}
ents = json.load(open(f"{OUT}/entities_canonical.json"))
random.seed(int(sys.argv[2]) if len(sys.argv) > 2 else 11)
cat = sys.argv[1]
groups = defaultdict(set)
for code, e in ents.items():
    for v in e[cat]:
        groups[(repo_of(recs[code]["source_id"]), v)].add(code)
cands = [(k, sorted(v)) for k, v in groups.items() if 2 <= len(v) <= 10]
for (repo, key), codes in random.sample(cands, 10):
    a, b = random.sample(codes, 2)
    print(f"[{repo} {key[:60]}]\n   {a}: {recs[a]['title'][:85]}\n   {b}: {recs[b]['title'][:85]}")
