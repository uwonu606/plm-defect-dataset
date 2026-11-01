import random
import sys
sys.path.insert(0, "analysis/round1/profile")
from extract import load, extract_all, CATEGORIES

recs = load("canonical")
random.seed(int(sys.argv[1]) if len(sys.argv) > 1 else 0)
for r in random.sample(recs, 4):
    e = extract_all(r)
    print("===", r["case_code"], r["source_id"])
    print(r["location"])
    for c in CATEGORIES:
        if e[c]:
            print(f"  {c}: {sorted(e[c])[:12]}")
