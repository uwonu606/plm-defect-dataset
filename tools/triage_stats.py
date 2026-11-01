import json, sys, re
from pathlib import Path

def github_fix_link(issue):
    for node in issue["timelineItems"]["nodes"]:
        if node["__typename"] == "ClosedEvent" and node.get("closer"):
            return node["closer"]["__typename"]
        if node["__typename"] == "CrossReferencedEvent" and (node.get("source") or {}).get("merged"):
            return "MergedPR"
    return None

for path in sys.argv[1:]:
    issues = [json.loads(l) for l in open(path, encoding="utf-8")]
    completed = [i for i in issues if i.get("stateReason") == "COMPLETED"]
    linked = [i for i in completed if github_fix_link(i)]
    commented = [i for i in completed if len(i["comments"]["nodes"]) >= 2]
    print(Path(path).name, "closed", len(issues), "completed", len(completed), "fix-linked", len(linked), "completed+2comments", len(commented))
