import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"

UPLOAD = re.compile(r"github\.com/(?:user-attachments/files|[^/\s]+/[^/\s]+/files)/|^/uploads/|gitlab\.[^/]+/.*/uploads/|launchpadlibrarian|\+attachment", re.I)
CI_LOG = re.compile(r"logs\.openstack\.org|zuul|opendev_logs|rackcdn\.com|/-/jobs/\d+|jenkins|mirror\.starlingx|cengn", re.I)
BEACON = re.compile(r"notifications/beacon", re.I)


def url_class(u):
    if UPLOAD.search(u):
        return "upload"
    if CI_LOG.search(u):
        return "ci_log"
    return "other_link"


def ext(u):
    p = u.split("?")[0].rstrip(".,").lower()
    for e in ("pcapng", "pcap", "tar.gz", "tgz", "zip", "log", "txt", "gz", "yaml", "yml", "conf", "cfg", "json", "csv", "xlsx", "xml", "html", "diff", "patch", "7z", "xz", "cap"):
        if p.endswith("." + e):
            return e
    return "other"


def group_ext(e):
    if e in ("pcap", "pcapng", "cap"):
        return "pcap"
    if e in ("zip", "tar.gz", "tgz", "gz", "7z", "xz"):
        return "archive"
    if e in ("log", "txt"):
        return "log_txt"
    if e in ("yaml", "yml", "conf", "cfg", "json", "xml"):
        return "config_data"
    if e in ("csv", "xlsx"):
        return "table"
    return "other"


def load():
    media = {}
    for line in (OUT / "media.jsonl").open(encoding="utf-8"):
        m = json.loads(line)
        media[m["sid"]] = m
    rows = []
    for line in (OUT / "features.jsonl").open(encoding="utf-8"):
        r = json.loads(line)
        m = media.get(r["sid"])
        f = {}
        imgs = []
        atts = []
        if m:
            imgs = [(a, u) for a, u in m["body_images"] + m["comment_images"] if not BEACON.search(u)]
            atts = m["body_attach"] + m["comment_attach"]
        b, c = r["body"], r["comments"]
        get = lambda k: (b.get(k) or 0) + (c.get(k) or 0)
        f["image"] = bool(imgs)
        f["image_n"] = len(imgs)
        f["image_body"] = bool(m and [u for a, u in m["body_images"] if not BEACON.search(u)])
        f["screenshot_like"] = bool(imgs) and any(re.search(r"screen ?shot|screen_shot|capture|^image(\.png)?$|^图片$", a.strip(), re.I) or a.strip() == "" and "user-images" in u for a, u in imgs) or bool(imgs) and get("screenshot_word") > 0
        classes = Counter(url_class(u) for u in atts)
        f["upload"] = classes["upload"] > 0
        f["ci_log"] = classes["ci_log"] > 0
        f["upload_exts"] = sorted({group_ext(ext(u)) for u in atts if url_class(u) == "upload"})
        f["pcap_file"] = any(re.search(r"pcap|\.cap$", u, re.I) for u in atts)
        f["pcap_any"] = f["pcap_file"] or get("pcap_mention") > 0
        f["attach_mention"] = get("attach_mention") > 0
        f["external_log"] = get("external_log") > 0
        f["fence20"] = get("fence_ge20") > 0
        f["fence50"] = get("fence_ge50") > 0
        f["fence200"] = get("fence_ge200") > 0
        f["logrun20"] = get("logrun_ge20") > 0
        f["longlog"] = f["fence20"] or f["logrun20"]
        f["stack"] = bool(b.get("stack") or c.get("stack"))
        f["stack_kinds"] = sorted(set((b.get("stack") or []) + (c.get("stack") or [])))
        f["config"] = get("config_dump") > 0
        f["qxdm"] = get("qxdm") > 0
        f["nontext"] = f["image"] or f["upload"]
        f["chars"] = get("chars")
        r["f"] = f
        rows.append(r)
    return rows


KEYS = ["image", "screenshot_like", "upload", "pcap_file", "pcap_any", "ci_log", "attach_mention", "longlog", "fence50", "stack", "config", "qxdm", "nontext"]


def pct(n, d):
    return f"{n}({100 * n / d:.1f}%)" if d else "-"


def table(rows, keyfn, title):
    groups = defaultdict(list)
    for r in rows:
        groups[keyfn(r)].append(r)
    print(f"\n## {title}")
    print("| group | N | " + " | ".join(KEYS) + " |")
    for g in sorted(groups):
        rs = groups[g]
        print(f"| {g} | {len(rs)} | " + " | ".join(pct(sum(bool(r['f'][k]) for r in rs), len(rs)) for k in KEYS) + " |")
    rs = rows
    print(f"| ALL | {len(rs)} | " + " | ".join(pct(sum(bool(r['f'][k]) for r in rs), len(rs)) for k in KEYS) + " |")


def main():
    rows = load()
    table(rows, lambda r: r["src"], "raw 전체, 소스별")
    ds = [r for r in rows if r["in_dataset"]]
    table(ds, lambda r: r["src"], "dataset 포함 10,000건, 소스별")
    table(ds, lambda r: r["equipment"], "dataset 포함, 장비군별")
    table([r for r in ds if r["src"].startswith(("github", "gitlab"))], lambda r: r["equipment"], "dataset ran-core 소스(github/gitlab)만, 장비군별")
    table(ds, lambda r: r["record_type"], "dataset 포함, record_type별")
    print("\n## upload 확장자 분포(dataset, 레코드 수)")
    print(Counter(e for r in ds for e in r["f"]["upload_exts"]))
    print("## stack 종류(dataset)")
    print(Counter(e for r in ds for e in r["f"]["stack_kinds"]))
    print("## 이미지 수 분포(dataset, image 있는 레코드)")
    print(Counter(min(r["f"]["image_n"], 5) for r in ds if r["f"]["image"]))
    print("## 이미지가 본문에 있는 비율(dataset image 레코드)")
    im = [r for r in ds if r["f"]["image"]]
    print(pct(sum(r["f"]["image_body"] for r in im), len(im)))
    print("## gitlab notes 손실")
    for src in ("gitlab:oai/openairinterface5g", "gitlab:ocudu/ocudu"):
        rs = [r for r in rows if r["src"] == src]
        print(src, "records", len(rs), "with notes>0", sum(r.get("user_notes_count", 0) > 0 for r in rs), "sum notes", sum(r.get("user_notes_count", 0) for r in rs))
    print("## github comment 상한 30에 닿은 레코드")
    for src in sorted({r["src"] for r in rows if r["src"].startswith("github")}):
        rs = [r for r in rows if r["src"] == src]
        print(src, sum(r["n_comments"] >= 30 for r in rs))
    print("## launchpad messages 상한 50(=49 comments)에 닿은 레코드")
    for src in ("launchpad:neutron", "launchpad:starlingx"):
        rs = [r for r in rows if r["src"] == src]
        print(src, sum(r["n_comments"] >= 49 for r in rs))


if __name__ == "__main__":
    main()
