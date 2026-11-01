import json, sys, collections
feat = sys.argv[1]
c = collections.Counter(); n = collections.Counter()
for line in open(feat):
    r = json.loads(line)
    if not r["in_dataset"]: continue
    g = (r["body"].get("external_log") or 0) + (r["comments"].get("external_log") or 0)
    n[r["src"]] += 1; n["ALL"] += 1
    if g: c[r["src"]] += 1; c["ALL"] += 1
for k in sorted(n): print(k, n[k], c[k], round(100*c[k]/n[k],1))
