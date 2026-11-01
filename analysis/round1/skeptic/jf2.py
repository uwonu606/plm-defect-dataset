import json, re, sys
from collections import Counter, defaultdict
from pathlib import Path
ROOT = Path(sys.argv[1])
canon = [json.loads(l) for l in open(ROOT/"dataset/canonical.jsonl", encoding="utf-8")]
want = {r["source_id"] for r in canon}
by_src = Counter(r["source_id"].rsplit("#",1)[0] for r in canon)
raw = {}
def key_for(path, rec):
    kind, *rest = path.stem.split("__"); name="/".join(rest)
    if kind=="github": return f"{name}#{rec['number']}"
    if kind=="gitlab": return f"{name}#{rec['iid']}"
    if kind=="launchpad": return f"launchpad:{name}#{rec['id']}"
    return f"rhbz#{rec['id']}"
for path in sorted((ROOT/"raw").glob("*.jsonl")):
    if "starlingx" in path.name: continue
    for line in open(path, encoding="utf-8"):
        rec=json.loads(line); k=key_for(path, rec)
        if k in want: raw[k]=(path.stem.split("__")[0], rec)
print("joined", len(raw), "of", len(want))
ISSUE_REF = re.compile(r"(?<![\w/&])#(\d{1,6})\b")
LP_REF = re.compile(r"(?:[Bb]ug[: ]*#?|\+bug/|Closes-Bug: #?|Related-Bug: #?|Partial-Bug: #?)(\d{6,7})")
stat = defaultdict(Counter); n = Counter(); edges = Counter(); intra = Counter()
for sid,(kind,r) in raw.items():
    repo = sid.rsplit("#",1)[0]; n[repo]+=1; s=stat[repo]
    refs=set()
    if kind=="github":
        if r["labels"]["nodes"]: s["labels"]+=1
        cm=r["comments"]["nodes"]
        if cm: s["comments"]+=1
        if any(x.get("author") for x in cm): s["comment_authors"]+=1
        prs=[nd for nd in r["timelineItems"]["nodes"] if (nd.get("closer") or nd.get("source") or {}).get("__typename")=="PullRequest"]
        com=[nd for nd in r["timelineItems"]["nodes"] if (nd.get("closer") or {}).get("__typename")=="Commit"]
        if prs: s["pr_link"]+=1
        if com: s["commit_link"]+=1
        if prs or com: s["fix_link"]+=1
        if any(((nd.get("source") or {}).get("repository") or {}).get("nameWithOwner","").lower()!=repo.lower() for nd in prs if nd.get("source")): s["cross_repo_pr"]+=1
        s["closed_at"]+=1
        text=(r["body"] or "")+"\n".join(x["body"] for x in cm)
        refs={f"{repo}#{m}" for m in ISSUE_REF.findall(text)}-{sid}
    elif kind=="gitlab":
        if r.get("labels"): s["labels"]+=1
        if r.get("milestone"): s["milestone"]+=1
        if r.get("assignees"): s["assignee"]+=1
        mrs=r.get("related_merge_requests") or []
        if mrs: s["fix_link"]+=1; s["pr_link"]+=1
        if any(m.get("sha") for m in mrs): s["commit_link"]+=1
        if r.get("user_notes_count"): s["comments(count only)"]+=1
        s["closed_at"]+=1
        text=(r.get("description") or "")+"\n".join((m.get("description") or "") for m in mrs)
        refs={f"{repo}#{m}" for m in ISSUE_REF.findall(text)}-{sid}
    elif kind=="launchpad":
        if r.get("tags"): s["labels"]+=1
        s["importance"]+= r.get("importance") not in (None,"Undecided")
        text="\n".join(r["messages"])
        if "Reviewed:" in text: s["fix_link"]+=1; s["pr_link"]+=1
        if re.search(r"\ncommit [0-9a-f]{40}", text): s["commit_link"]+=1
        if re.search(r"Branch:\s+stable/", text) or any(t.startswith("in-stable-") for t in r.get("tags") or []): s["backport_branch"]+=1
        if "This issue was fixed in the" in text: s["fixed_release"]+=1
        if len(r["messages"])>1: s["comments"]+=1
        refs={f"launchpad:neutron#{m}" for m in LP_REF.findall(r["description"]+"\n"+text)}-{sid}
    else:
        s["labels"]+=1
        if r.get("cf_fixed_in"): s["fixed_release"]+=1
        s["version"]+= bool(r.get("version"))
        s["component"]+= bool(r.get("component"))
    if refs: s["mentions_other_issue"]+=1
    hit = refs & want
    if hit: s["mentions_issue_in_dataset"]+=1; edges[repo]+=len(hit)
tot=Counter()
for repo in sorted(n, key=lambda k:-n[k]):
    print(f"== {repo} (dataset {n[repo]})")
    print("   ", {k: f"{v/n[repo]:.0%}" for k,v in sorted(stat[repo].items())}, "intra-dataset edges:", edges[repo])
    for k,v in stat[repo].items(): tot[k]+=v
N=sum(n.values())
print("== ALL", N, {k: f"{v/N:.1%}" for k,v in sorted(tot.items())}, "edges", sum(edges.values()))

# edge distribution check
import random
random.seed(1)
per=[]
for sid,(kind,r) in raw.items():
    repo = sid.rsplit("#",1)[0]
    if kind=="launchpad":
        text=r["description"]+"\n"+"\n".join(r["messages"])
        refs={f"launchpad:neutron#{m}" for m in LP_REF.findall(text)}-{sid}
    elif kind=="gitlab":
        text=(r.get("description") or "")+"\n".join((m.get("description") or "") for m in r.get("related_merge_requests") or [])
        refs={f"{repo}#{m}" for m in ISSUE_REF.findall(text)}-{sid}
    elif kind=="github":
        text=(r["body"] or "")+"\n".join(x["body"] for x in r["comments"]["nodes"])
        refs={f"{repo}#{m}" for m in ISSUE_REF.findall(text)}-{sid}
    else: continue
    hit=refs&want
    if hit: per.append((len(hit),sid,sorted(hit)[:3]))
per.sort(reverse=True)
print("top:", per[:6])
print("records with >=1 edge", len(per), "median hits", sorted(x[0] for x in per)[len(per)//2])
for x in random.sample(per,6): print("sample", x)
from collections import Counter as C2
small=C2(x[1].rsplit('#',1)[0] for x in per if x[0]<=3)
print("records with 1-3 intra-dataset refs by source:", dict(small), "total", sum(small.values()))
fix_to = defaultdict(set)
for sid,(kind,r) in raw.items():
    repo = sid.rsplit("#",1)[0]
    keys=set()
    if kind=="github":
        for nd in r["timelineItems"]["nodes"]:
            s=nd.get("closer") or nd.get("source") or {}
            if s.get("__typename")=="PullRequest" and s.get("merged"): keys.add(("pr", s["url"]))
            if s.get("__typename")=="Commit": keys.add(("c", s["oid"]))
    elif kind=="gitlab":
        for m in r.get("related_merge_requests") or []:
            if m.get("state")=="merged": keys.add(("mr", m["web_url"]))
    elif kind=="launchpad":
        for m in r["messages"]:
            if "Reviewed:" in m:
                for sha in re.findall(r"\ncommit ([0-9a-f]{40})", m): keys.add(("c", sha))
    for k in keys: fix_to[k].add(sid)
shared=[v for v in fix_to.values() if 1<len(v)<=5]
recs=set().union(*shared) if shared else set()
cby=Counter(s.rsplit('#',1)[0] for s in recs)
print("fix keys", len(fix_to), "shared(2-5) groups", len(shared), "records in shared-fix groups", len(recs), dict(cby))
# compare with canonical cause_class / duplicate
cc={r["source_id"]:(r["cause_class"],r["cause_basis"]) for r in canon}
same=sum(1 for g in shared if len({cc[s][0] for s in g})==1)
print("groups whose members share cause_class:", same, "/", len(shared))
uniq={frozenset(g) for g in shared}
same=sum(1 for g in uniq if len({cc[s][0] for s in g})==1)
both_explicit=sum(1 for g in uniq if all(cc[s][1]=="명시" for s in g))
print("unique groups", len(uniq), "same cause_class", same, "all members 명시", both_explicit)
for g in list(uniq)[:4]:
    print([ (s, cc[s]) for s in g])
org={r["source_id"]:r["origin"] for r in canon}
ex=[g for g in uniq if all(cc[s][1]=="명시" for s in g)]
print("SKEPTIC all-명시 groups",len(ex),"by origin",Counter(frozenset(org[s] for s in g) for g in ex))
print("SKEPTIC all-명시 & same cause_class",sum(1 for g in ex if len({cc[s][0] for s in g})==1))
print("SKEPTIC all-명시 by repo",Counter(next(iter(g)).rsplit('#',1)[0] for g in ex))
