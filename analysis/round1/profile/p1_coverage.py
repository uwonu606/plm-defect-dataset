import json
import sys
from collections import Counter
sys.path.insert(0, "analysis/round1/profile")
from extract import load, extract_corpus, CATEGORIES

OUT = "analysis/round1/profile/out"
corpus_name = sys.argv[1] if len(sys.argv) > 1 else "canonical"
recs = load(corpus_name)
ents = extract_corpus(recs)

with open(f"{OUT}/entities_{corpus_name}.json", "w") as f:
    json.dump({k: {c: sorted(v) for c, v in e.items()} for k, e in ents.items()}, f, ensure_ascii=False)


def coverage_table(group_key):
    groups = {}
    for r in recs:
        groups.setdefault(r[group_key], []).append(r["case_code"])
    groups["ALL"] = [r["case_code"] for r in recs]
    cols = [g for g in sorted(groups, key=lambda g: -len(groups[g]))]
    print(f"\n## coverage by {group_key} ({corpus_name}) : % of records with >=1 entity")
    print("category".ljust(14) + "".join(f"{g[:16]:>18}" for g in cols))
    print("n".ljust(14) + "".join(f"{len(groups[g]):>18}" for g in cols))
    for c in CATEGORIES + ["ANY_TELECOM", "CODE_ANY", "TELECOM_AND_CODE"]:
        row = []
        for g in cols:
            ids = groups[g]
            if c == "ANY_TELECOM":
                hit = sum(1 for i in ids if ents[i]["nf"] or ents[i]["iface"])
            elif c == "CODE_ANY":
                hit = sum(1 for i in ids if ents[i]["func"] or ents[i]["file"])
            elif c == "TELECOM_AND_CODE":
                hit = sum(1 for i in ids if (ents[i]["nf"] or ents[i]["iface"]) and (ents[i]["func"] or ents[i]["file"]))
            else:
                hit = sum(1 for i in ids if ents[i][c])
            row.append(f"{100 * hit / len(ids):17.1f}%")
        print(c.ljust(14) + "".join(row))


coverage_table("origin")
coverage_table("equipment")

print(f"\n## distinct values and top values ({corpus_name})")
for c in CATEGORIES:
    cnt = Counter(v for e in ents.values() for v in e[c])
    print(f"{c}: distinct={len(cnt)} top={cnt.most_common(8)}")

print("\n## mean entities per record by category (records with >=1)")
for c in CATEGORIES:
    vals = [len(e[c]) for e in ents.values() if e[c]]
    if vals:
        print(f"{c}: mean={sum(vals)/len(vals):.2f}")
