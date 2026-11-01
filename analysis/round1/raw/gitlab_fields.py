import json, sys, glob
from collections import Counter
for path in sorted(glob.glob(sys.argv[1] + "/gitlab__*.jsonl")):
    n=0; c=Counter(); labels=Counter(); sev=Counter(); itype=Counter(); ms=Counter(); sysnotes=Counter(); tb=Counter(); notes_n=[]; assignees=Counter(); mrlabels=Counter()
    for line in open(path, encoding="utf-8"):
        i=json.loads(line); n+=1
        if i.get("labels"): c["labels"]+=1
        labels.update(i.get("labels") or [])
        sev[i.get("severity")]+=1; itype[i.get("issue_type")]+=1
        if i.get("milestone"): c["milestone"]+=1; ms[i["milestone"]["title"]]+=1
        if i.get("assignees"): c["assignee"]+=1; assignees.update(a["username"] for a in i["assignees"])
        if (i.get("_links") or {}).get("closed_as_duplicate_of"): c["closed_as_duplicate_of"]+=1
        if i.get("moved_to_id"): c["moved_to"]+=1
        if i.get("epic"): c["epic"]+=1
        if i.get("user_notes_count"): c["user_notes_count>0"]+=1
        notes=i.get("notes") or []
        notes_n.append(len(notes))
        if notes: c["notes_collected"]+=1
        if any(x.get("system") for x in notes): c["system_notes"]+=1
        for x in notes:
            if x.get("system"):
                b=x["body"]
                for key in ("mentioned in merge request","mentioned in commit","mentioned in issue","marked this issue as","added ~","removed ~","changed milestone","assigned to","closed via","closed","reopened","changed the description","changed title"):
                    if b.startswith(key) or key in b[:40]:
                        sysnotes[key]+=1; break
                else: sysnotes["other:"+b[:30]]+=0
        mrs=i.get("related_merge_requests") or []
        if mrs: c["related_mr"]+=1
        if any(m.get("state")=="merged" for m in mrs): c["merged_mr"]+=1
        for m in mrs:
            tb[m.get("target_branch")]+=1; mrlabels.update(m.get("labels") or [])
        if any(m.get("merge_commit_sha") or m.get("squash_commit_sha") or m.get("sha") for m in mrs): c["mr_sha"]+=1
    print(f"== {path.split('__',1)[1]} n={n}")
    print("  fill:", {k: f"{v/n:.1%}" for k,v in sorted(c.items())})
    print("  severity:", dict(sev), " issue_type:", dict(itype))
    print("  notes collected median/max:", sorted(notes_n)[n//2], max(notes_n))
    print("  system note kinds:", {k:v for k,v in sysnotes.most_common(15) if v})
    print("  top labels:", labels.most_common(25))
    print("  milestones:", ms.most_common(8))
    print("  distinct assignees:", len(assignees))
    print("  MR target branches:", tb.most_common(6))
    print("  MR labels:", mrlabels.most_common(10))
