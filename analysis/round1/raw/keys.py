import json, sys
from collections import Counter

def filled(v):
    return v not in (None, "", [], {}, 0, False)

def walk(obj, prefix, top, fill, depth=0):
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else k
            top[p] += 1
            if filled(v): fill[p] += 1
            if depth < 2 and isinstance(v, dict):
                walk(v, p, top, fill, depth + 1)
            if depth < 1 and isinstance(v, list) and v and isinstance(v[0], dict):
                for item in v[:1]:
                    walk(item, p + "[]", top, fill, depth + 1)

path, limit = sys.argv[1], int(sys.argv[2])
top, fill = Counter(), Counter()
n = 0
for line in open(path, encoding="utf-8"):
    walk(json.loads(line), "", top, fill)
    n += 1
    if n >= limit: break
print(f"== {path.split('/')[-1]} sampled {n}")
for k in sorted(top):
    if "[]" in k and top[k] < n * 0.01: continue
    print(f"  {k:55s} present {top[k]/n:6.1%}  filled {fill[k]/n:6.1%}")
