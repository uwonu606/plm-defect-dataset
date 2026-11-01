import json
import random
import re
import sys
sys.path.insert(0, "analysis/round1/profile")
from extract import load, record_text, repo_of

OUT = "analysis/round1/profile/out"
recs = {r["case_code"]: r for r in load("canonical")}
pairs = json.load(open(f"{OUT}/xref_pairs.json"))
random.seed(7)
for a, b in random.sample(pairs, 25):
    ra, rb = recs[a], recs[b]
    for src, dst in [(ra, rb), (rb, ra)]:
        num = dst["source_id"].split("#")[1]
        m = re.search(r".{0,50}(?<!\d)" + re.escape(num) + r"(?!\d).{0,30}", record_text(src))
        if m:
            print(f"{src['case_code']} -> {dst['case_code']} | {m.group(0)!r}")
            print(f"     dst title: {dst['title'][:80]}")
            break
