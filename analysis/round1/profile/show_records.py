import json
import sys
sys.path.insert(0, "analysis/round1/profile")
from extract import load

recs = {r["case_code"]: r for r in load("canonical")}
for code in sys.argv[1:]:
    r = recs[code]
    print(f"=== {code} {r['source_id']} [{r['cause_basis']}/{r['cause_class']}] dup={r['duplicate_of_case']}")
    for f in ["title", "location", "problem", "cause", "resolution"]:
        print(f"  {f}: {r[f][:420]}")
