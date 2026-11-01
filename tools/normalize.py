import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
OUT = ROOT / "work" / "candidates.jsonl"

BODY_LIMIT = 3000
DISCUSSION_LIMIT = 2500
FIX_LIMIT = 2000
BOT_LOGINS = re.compile(r"bot|github-actions", re.I)

LICENSES = {
    "open5gs/open5gs": "GitHub 이슈(GitHub 약관), 저장소 AGPL-3.0",
    "free5gc/free5gc": "GitHub 이슈(GitHub 약관), 저장소 Apache-2.0",
    "magma/magma": "GitHub 이슈(GitHub 약관)",
    "srsran/srsRAN_Project": "GitHub 이슈(GitHub 약관)",
    "srsran/srsRAN_4G": "GitHub 이슈(GitHub 약관)",
    "duranta-project/openairinterface5g": "GitHub 이슈(GitHub 약관), 저장소 OAI CSSL v1.0",
    "ocudu/ocudu": "GitLab 이슈(GitLab 약관), 저장소 BSD-3-Clause",
    "oai/openairinterface5g": "GitLab 이슈(Eurecom GitLab), 저장소 OAI CSSL v1.0",
    "starlingx": "Launchpad 버그(Launchpad 약관), 저장소 Apache-2.0",
    "neutron": "Launchpad 버그(Launchpad 약관), 저장소 Apache-2.0",
    "redhat": "Red Hat Bugzilla(Red Hat 약관)",
}

PRIORITY = {"ran-core": 0, "adjacent-network": 1, "adjacent-platform": 2}


def clip(text, limit):
    text = re.sub(r"<!--.*?-->", "", text or "", flags=re.S)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text[:limit]


def joined(parts, limit):
    return clip("\n---\n".join(p for p in parts if p), limit)


def from_github(issue, repo):
    fix_refs = []
    for node in issue["timelineItems"]["nodes"]:
        source = node.get("closer") if node["__typename"] == "ClosedEvent" else node.get("source")
        if not source:
            continue
        if source.get("__typename") == "PullRequest":
            fix_refs.append(f"PR #{source['number']} {source['title']}\n{source.get('body') or ''}")
        elif source.get("__typename") == "Commit":
            fix_refs.append(f"commit {source['oid'][:9]}\n{source['message']}")
    comments = [c["body"] for c in issue["comments"]["nodes"] if c["author"] and not BOT_LOGINS.search(c["author"]["login"])]
    return {
        "source_id": f"{repo}#{issue['number']}",
        "url": issue["url"],
        "created": issue["createdAt"][:10],
        "title": issue["title"],
        "labels": [l["name"] for l in issue["labels"]["nodes"]],
        "body": issue["body"],
        "discussion": comments,
        "fix_refs": fix_refs,
        "skip": issue.get("stateReason") == "NOT_PLANNED",
    }


def from_gitlab(issue, project):
    merged = [f"MR !{m['iid']} {m['title']}\n{m.get('description') or ''}" for m in issue.get("related_merge_requests", []) if m.get("state") == "merged"]
    notes = [n["body"] for n in issue.get("notes", []) if not n.get("system")]
    return {
        "source_id": f"{project}#{issue['iid']}",
        "url": issue["web_url"],
        "created": issue["created_at"][:10],
        "title": issue["title"],
        "labels": issue.get("labels", []),
        "body": issue.get("description"),
        "discussion": notes,
        "fix_refs": merged,
        "skip": False,
    }


def from_launchpad(bug, project):
    merged = [m for m in bug["messages"] if "Fix merged" in m or "Reviewed:" in m]
    others = [m for m in bug["messages"][1:] if m not in merged]
    return {
        "source_id": f"launchpad:{project}#{bug['id']}",
        "url": bug["web_link"],
        "created": (bug.get("created") or "")[:10],
        "title": bug["title"],
        "labels": bug["tags"],
        "body": bug["description"],
        "discussion": others,
        "fix_refs": merged,
        "skip": False,
    }


def from_bugzilla(bug):
    components = bug.get("component", [])
    return {
        "source_id": f"rhbz#{bug['id']}",
        "url": f"https://bugzilla.redhat.com/show_bug.cgi?id={bug['id']}",
        "created": bug.get("creation_time", "")[:10],
        "title": bug.get("summary", ""),
        "labels": [bug.get("product", "")] + components + bug.get("version", []),
        "body": bug.get("cf_release_notes", ""),
        "discussion": [],
        "fix_refs": [f"fixed in {', '.join(bug['cf_fixed_in'])}"] if bug.get("cf_fixed_in") else [],
        "skip": not bug.get("cf_release_notes"),
    }


def tier_for(path, record):
    if path.name.startswith(("github__", "gitlab__")):
        return "ran-core"
    if path.name.startswith("launchpad__neutron"):
        return "adjacent-network"
    if path.name.startswith("bugzilla__") and re.search(r"neutron|ovn|openvswitch|networkmanager|dpdk|sriov|network", " ".join(record["labels"]), re.I):
        return "adjacent-network"
    return "adjacent-platform"


def records():
    for path in sorted(RAW.glob("*.jsonl")):
        kind, *rest = path.stem.split("__")
        name = "/".join(rest)
        for line in path.open(encoding="utf-8"):
            raw = json.loads(line)
            if kind == "github":
                record = from_github(raw, name)
            elif kind == "gitlab":
                record = from_gitlab(raw, name)
            elif kind == "launchpad":
                record = from_launchpad(raw, name)
            else:
                record = from_bugzilla(raw)
            if record.pop("skip") or "Migrated from GitLab" in (record["body"] or ""):
                continue
            record["tier"] = tier_for(path, record)
            record["license"] = LICENSES.get(name.split("/")[-1] if kind in ("launchpad", "bugzilla") else name, LICENSES["redhat"])
            record["body"] = clip(record["body"], BODY_LIMIT)
            record["discussion"] = joined(record["discussion"], DISCUSSION_LIMIT)
            record["fix_refs"] = joined(record["fix_refs"], FIX_LIMIT)
            yield record


def main():
    OUT.parent.mkdir(exist_ok=True)
    rows = sorted(records(), key=lambda r: (PRIORITY[r["tier"]], r["source_id"]))
    with OUT.open("w", encoding="utf-8") as out:
        for row in rows:
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
    by_tier = {}
    chars = 0
    for row in rows:
        by_tier[row["tier"]] = by_tier.get(row["tier"], 0) + 1
        chars += sum(len(row[k]) for k in ("title", "body", "discussion", "fix_refs"))
    print(json.dumps({"rows": len(rows), "by_tier": by_tier, "approx_input_tokens": chars // 4}, ensure_ascii=False))


if __name__ == "__main__":
    main()
