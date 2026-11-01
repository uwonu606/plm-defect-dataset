import json, sys, re
from collections import Counter
PAT = {
 "fix_merged": re.compile(r"Fix merged to (\S+) \(([^)]+)\)"),
 "fix_proposed": re.compile(r"Fix proposed to (\S+) \(([^)]+)\)"),
 "related_fix": re.compile(r"Related fix (merged|proposed)"),
 "reviewed_url": re.compile(r"Reviewed:\s+https://review\.\S+"),
 "commit_sha": re.compile(r"\ncommit ([0-9a-f]{40})"),
 "change_id": re.compile(r"Change-Id: (I[0-9a-f]{40})"),
 "closes_bug": re.compile(r"(Closes|Partial|Related)-Bug: #?(\d+)", re.I),
 "fixed_in_release": re.compile(r"This issue was fixed in the (\S+) (\S+) (release|release candidate)"),
 "dup_of": re.compile(r"duplicate of bug #?\d+", re.I),
 "other_bug_ref": re.compile(r"(?:bug|lp)\s*#\s*\d{6,7}|bugs\.launchpad\.net/\S+/\+bug/\d+", re.I),
 "author_line": re.compile(r"^Author: .+$", re.M),
 "date_line": re.compile(r"^Date:\s+.+$", re.M),
 "story_task": re.compile(r"storyboard|Story: \d+"),
}
path, limit = sys.argv[1], int(sys.argv[2])
n=0; c=Counter(); tags=Counter(); imp=Counter(); st=Counter(); branches=Counter(); releases=Counter(); msgs=[]; repos=Counter()
for line in open(path, encoding="utf-8"):
    b=json.loads(line); n+=1
    if b.get("tags"): c["tags"]+=1
    tags.update(b.get("tags") or []); imp[b.get("importance")]+=1; st[b.get("status")]+=1
    ms=b["messages"]; msgs.append(len(ms))
    if len(ms)>=50: c["messages_capped50"]+=1
    text="\n".join(ms)
    for k,p in PAT.items():
        if p.search(text): c[k]+=1
    for repo, br in PAT["fix_merged"].findall(text): branches[br]+=1; repos[repo]+=1
    for proj, rel, _ in PAT["fixed_in_release"].findall(text): releases[proj]+=1
    if re.search(r"\b(Rocky|Stein|Train|Ussuri|Victoria|Wallaby|Xena|Yoga|Zed|202[3-6]\.[12])\b|\bstx\.\d", b["description"]): c["release_name_in_desc"]+=1
    if n>=limit: break
print(f"== {path.split('/')[-1]} sampled {n}")
print("  fill:", {k: f"{v/n:.1%}" for k,v in sorted(c.items())})
print("  importance:", dict(imp)); print("  status:", dict(st))
m=sorted(msgs); print("  messages median/p90/max:", m[n//2], m[int(n*.9)], m[-1])
print("  top tags:", tags.most_common(25))
print("  fix branches:", branches.most_common(10))
print("  fix repos:", repos.most_common(10))
print("  release-note projects:", releases.most_common(6))
