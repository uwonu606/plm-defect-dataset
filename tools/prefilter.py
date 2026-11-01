import json, re, sys
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "raw"
NON_DEFECT = re.compile(r"enhancement|feature|question|doc|ci|test|build|wishlist|gate-failure|support|duplicate|invalid|wontfix", re.I)
FIX_HINT = re.compile(r"\b(fix(ed|es)?|root cause|caused by|patch(ed)?|resolved)\b", re.I)

def github(i):
    labels = [l["name"] for l in i["labels"]["nodes"]]
    texts = [c["body"] for c in i["comments"]["nodes"]] + [str(n) for n in i["timelineItems"]["nodes"]]
    return i.get("stateReason") == "COMPLETED", labels, i["body"] or "", texts

def gitlab(i):
    texts = [n["body"] for n in i.get("notes", [])] + [m["title"] + (m.get("description") or "") for m in i.get("related_merge_requests", []) if m.get("state") == "merged"]
    return True, i.get("labels", []), i.get("description") or "", texts

def launchpad(b):
    return True, b["tags"], b["description"] or "", b["messages"]

def bugzilla(b):
    return True, b.get("component", []), b.get("summary", ""), [b.get("cf_release_notes", "")]

ADAPTERS = {"github": github, "gitlab": gitlab, "launchpad": launchpad, "bugzilla": bugzilla}

total = 0
for path in sorted(RAW.glob("*.jsonl")) :
    adapter = ADAPTERS[path.name.split("__")[0]]
    kept = 0
    rows = 0
    for line in open(path, encoding="utf-8"):
        rows += 1
        completed, labels, body, texts = adapter(json.loads(line))
        if not completed or any(NON_DEFECT.search(l) for l in labels) or len(body) < 150:
            continue
        if any(FIX_HINT.search(t or "") for t in texts):
            kept += 1
    total += kept
    print(f"{path.name:55s} {rows:6d} -> {kept:6d}")
print("total candidates", total)
