import json, sys, re, glob
from collections import Counter
ISSUE_REF = re.compile(r"(?<![\w/])#(\d{1,6})\b")
DUP = re.compile(r"duplicate (of )?#?\d+", re.I)
VER = re.compile(r"\bv?\d+\.\d+(\.\d+)?\b")
for path in sorted(glob.glob(sys.argv[1] + "/github__*.jsonl")):
    n=0; c=Counter(); labels=Counter(); reasons=Counter(); comment_counts=[]; authors=Counter(); closer=Counter(); xref_repo=Counter()
    for line in open(path, encoding="utf-8"):
        i=json.loads(line); n+=1
        ls=[l["name"] for l in i["labels"]["nodes"]]
        labels.update(ls)
        if ls: c["labels"]+=1
        reasons[i.get("stateReason")]+=1
        cm=i["comments"]["nodes"]; comment_counts.append(len(cm))
        if cm: c["comments>0"]+=1
        if len(cm)>=30: c["comments_capped30"]+=1
        if any(x.get("author") for x in cm): c["comment_author"]+=1
        for x in cm:
            if x.get("author"): authors[x["author"]["login"]]+=1
        nodes=i["timelineItems"]["nodes"]
        has_pr=has_commit=has_xref=has_merged=False
        for nd in nodes:
            if nd["__typename"]=="ClosedEvent":
                cl=nd.get("closer")
                closer[(cl or {}).get("__typename")]+=1
                if cl and cl.get("__typename")=="PullRequest": has_pr=True; has_merged |= bool(cl.get("merged"))
                if cl and cl.get("__typename")=="Commit": has_commit=True
            elif nd["__typename"]=="CrossReferencedEvent":
                s=nd.get("source") or {}
                if s.get("__typename")=="PullRequest":
                    has_xref=True; xref_repo[(s.get("repository") or {}).get("nameWithOwner")]+=1
                    has_merged |= bool(s.get("merged"))
        c["closer_pr"]+=has_pr; c["closer_commit"]+=has_commit; c["xref_pr"]+=has_xref; c["any_fix_link"]+=(has_pr or has_commit or has_xref); c["merged_pr"]+=has_merged
        text=(i["body"] or "")+" ".join(x["body"] for x in cm)
        if ISSUE_REF.search(text): c["issue_ref_#N_in_text"]+=1
        if DUP.search(text): c["dup_phrase"]+=1
        if VER.search(i["body"] or ""): c["version_in_body"]+=1
        if i.get("closedAt"): c["closedAt"]+=1
    name=path.split("__",1)[1]
    print(f"== {name} n={n}")
    print("  fill:", {k: f"{v/n:.1%}" for k,v in sorted(c.items())})
    print("  stateReason:", dict(reasons))
    print("  closer types:", dict(closer))
    cc=sorted(comment_counts); print("  comments median/p90/max:", cc[n//2], cc[int(n*.9)], cc[-1])
    print("  distinct comment authors:", len(authors))
    print("  top labels:", labels.most_common(15))
    print("  xref repos:", xref_repo.most_common(5))
