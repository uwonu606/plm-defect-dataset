import json, re, sys
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "raw"
FIX_WORDS = re.compile(r"\b(fix(ed)?|root cause|caused by|because|patch)\b", re.I)

def clip(text, n):
    text = re.sub(r"```.*?```", "[code]", text or "", flags=re.S)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:n]

def github(issue):
    prs = []
    for node in issue["timelineItems"]["nodes"]:
        src = node.get("closer") if node["__typename"] == "ClosedEvent" else node.get("source")
        if src and src.get("__typename") == "PullRequest" and (src.get("merged") or node["__typename"] == "ClosedEvent"):
            prs.append(f"PR#{src['number']} {src['title']} :: {clip(src.get('body'), 400)}")
        if src and src.get("__typename") == "Commit":
            prs.append(f"commit {clip(src['message'], 400)}")
    comments = [c["body"] for c in issue["comments"]["nodes"] if c["author"] and "bot" not in c["author"]["login"] and "github-actions" not in c["author"]["login"]]
    fix_comments = [clip(c, 350) for c in comments if FIX_WORDS.search(c)][:3]
    return issue["url"], issue["title"], clip(issue["body"], 900), prs[:2], fix_comments

def gitlab(issue):
    mrs = [f"MR!{m['iid']} {m['title']} :: {clip(m.get('description'), 400)}" for m in issue.get("related_merge_requests", []) if m.get("state") == "merged"]
    notes = [clip(n["body"], 350) for n in issue.get("notes", []) if not n.get("system") and FIX_WORDS.search(n["body"])][:3]
    return issue["web_url"], issue["title"], clip(issue.get("description"), 900), mrs[:2], notes

def launchpad(bug):
    merged = [clip(m, 600) for m in bug["messages"] if "Fix merged" in m or "Reviewed:" in m][:1]
    return bug["web_link"], bug["title"], clip(bug["description"], 900), merged, []

def candidates(path, adapter, want):
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    picked = []
    for row in rows[::max(1, len(rows) // (want * 15))]:
        url, title, body, fixes, comments = adapter(row)
        if fixes and len(body) > 200:
            picked.append((url, title, body, fixes, comments))
        if len(picked) == want:
            break
    return picked

PLAN = [
    ("github__open5gs__open5gs.jsonl", github, 3), ("github__free5gc__free5gc.jsonl", github, 3),
    ("github__magma__magma.jsonl", github, 3), ("github__srsran__srsRAN_Project.jsonl", github, 3),
    ("github__srsran__srsRAN_4G.jsonl", github, 2), ("gitlab__oai__openairinterface5g.jsonl", gitlab, 3),
    ("gitlab__ocudu__ocudu.jsonl", gitlab, 3), ("launchpad__starlingx.jsonl", launchpad, 3),
    ("launchpad__neutron.jsonl", launchpad, 3),
]
for name, adapter, want in PLAN:
    for url, title, body, fixes, comments in candidates(RAW / name, adapter, want):
        print(f"##### {url}\nTITLE: {title}\nBODY: {body}")
        for f in fixes: print("FIX:", f)
        for c in comments: print("NOTE:", c)
        print()
