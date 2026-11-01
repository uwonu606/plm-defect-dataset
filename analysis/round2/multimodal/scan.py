import json
import re
import sys
from pathlib import Path

ROOT = Path(".")
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)

IMG_EXT = r"(?:png|jpe?g|gif|bmp|webp|svg|tiff?)"
FILE_EXT = r"(?:log|txt|pcapng|pcap|cap|zip|tar\.gz|tgz|gz|xz|bz2|7z|xlsx|xls|csv|json|ya?ml|conf|cfg|ini|xml|qmdl|isf|dlf|hdf5?|core|diff|patch)"

IMAGE_PATTERNS = {
    "md_img": re.compile(r"!\[([^\]]*)\]\(([^)\s]+)"),
    "html_img": re.compile(r"<img\b[^>]*?src=[\"']?([^\"'\s>]+)", re.I),
}
IMAGE_URL = re.compile(
    r"https?://(?:user-images\.githubusercontent\.com|private-user-images\.githubusercontent\.com)/\S+"
    r"|https?://github\.com/user-attachments/assets/[0-9a-f-]+"
    r"|https?://github\.com/[^/\s]+/[^/\s]+/assets/\d+/[0-9a-f-]+"
    r"|https?://[^\s)\]>\"']+\." + IMG_EXT + r"(?:\?[^\s)\]>\"']*)?(?=[\s)\]>\"'.,]|$)"
    r"|/uploads/[0-9a-f]{32}/[^\s)\]>\"']+\." + IMG_EXT,
    re.I,
)
ATTACH_URL = re.compile(
    r"https?://github\.com/(?:user-attachments/files/\d+|[^/\s]+/[^/\s]+/files/\d+)/[^\s)\]>\"']+"
    r"|/uploads/[0-9a-f]{32}/[^\s)\]>\"']+"
    r"|https?://(?:launchpadlibrarian\.net|bugs\.launchpad\.net/[^\s]*\+attachment)/[^\s)\]>\"']+"
    r"|https?://[^\s)\]>\"']+\." + FILE_EXT + r"(?=[\s)\]>\"'.,]|$)",
    re.I,
)
EXTERNAL_LOG = re.compile(
    r"https?://(?:paste\.openstack\.org|pastebin\.com|gist\.github\.com|hastebin|dpaste|termbin|paste\.ubuntu\.com|bpa\.st"
    r"|logs\.openstack\.org|zuul\.opendev\.org|storage\.\S+?/zuul_opendev_logs|[^\s/]*\.?logs?\.[^\s/]+|gitlab\.com/[^\s]*/-/jobs/\d+"
    r"|drive\.google\.com|docs\.google\.com|dropbox\.com|wetransfer)\S*",
    re.I,
)
PCAP_MENTION = re.compile(r"\bpcap(?:ng)?s?\b|wireshark|tcpdump|tshark|\.pcap", re.I)
ATTACH_MENTION = re.compile(r"\battachments?\b|\b(?:i|we)(?:'ve| have)? (?:attach|attached|uploaded)\b|\battach(?:ed|ing)? (?:is |are )?(?:the |a |my |our |here|below|above|file|log|pcap|trace|screenshot|config|wireshark|core|full|both|two|some|all)|\b(?:log|logs|pcap|pcaps|file|files|trace|traces|capture|screenshot|config)s? (?:is |are )?attached\b|please find attached|see attached", re.I)
SCREENSHOT_WORD = re.compile(r"screen ?shot|screen capture|스크린샷|화면 캡처", re.I)
QXDM = re.compile(r"\bqxdm\b|\bqcat\b|\bqmdl\b|\bisf\b log", re.I)

STACK = {
    "python": re.compile(r"Traceback \(most recent call last\)"),
    "gdb_bt": re.compile(r"(?m)^\s*#\d+\s+(?:0x[0-9a-f]+ in \S+|\S+ \(.*\) at \S+:\d+)"),
    "glibc_bt": re.compile(r"\(\+0x[0-9a-f]+\)\s*\[0x[0-9a-f]+\]|\[0x[0-9a-f]{6,}\]\s*$", re.M),
    "sanitizer": re.compile(r"(?:Address|Leak|UndefinedBehavior|Thread|Memory)Sanitizer"),
    "go": re.compile(r"goroutine \d+ \[|^panic: ", re.M),
    "java": re.compile(r"(?m)^\s+at [\w.$<>]+\([\w]+\.java:\d+\)"),
    "kernel": re.compile(r"Call Trace:|Kernel panic"),
}
CRASH_WORD = re.compile(r"segmentation fault|core dumped|SIGSEGV|SIGABRT|assertion .*failed|ogs_assert", re.I)

FENCE = re.compile(r"(?ms)^[ \t]*(```+|~~~+)[ \t]*([\w+.-]*)[^\n]*\n(.*?)^[ \t]*\1[ \t]*$")
LOG_LINE = re.compile(
    r"^\s*(?:\[?\d{4}[-/]\d{2}[-/]\d{2}[ T]\d{2}:\d{2}|\[?\d{2}/\d{2}(?:/\d{2,4})? \d{2}:\d{2}|\[?\d{2}:\d{2}:\d{2}"
    r"|\w{3}\s+\d{1,2} \d{2}:\d{2}:\d{2}|\[\s*\d+\.\d+\]|\d{10}\.\d+|(?:DEBUG|INFO|WARN(?:ING)?|ERROR|CRITICAL|FATAL)\b"
    r"|\[[A-Z0-9_-]{2,12}\]\s|\d+\.\d+\s+\[)"
)
CONFIG_LINE = re.compile(r"^\s*(?:-\s+)?[\w.\-\[\]\"']+\s*(?::(?:\s|$)|=)")
CONFIG_LANG = {"yaml", "yml", "ini", "conf", "cfg", "toml", "properties", "libconfig"}
DATA_LANG = {"json", "xml"}


def blocks(text):
    found = []
    for m in FENCE.finditer(text):
        lines = [l for l in m.group(3).split("\n") if l.strip()]
        found.append((m.group(2).lower(), lines, m.start()))
    return found


def log_runs(text, minimum):
    run = gap = 0
    best = 0
    count = 0
    for line in text.split("\n"):
        if LOG_LINE.match(line):
            run += 1
            gap = 0
        elif run and gap < 3:
            gap += 1
            run += 1
        else:
            if run >= minimum:
                count += 1
            best = max(best, run)
            run = gap = 0
    if run >= minimum:
        count += 1
    return count, max(best, run)


def config_runs(text, minimum=8):
    run = 0
    count = 0
    for line in text.split("\n"):
        if CONFIG_LINE.match(line):
            run += 1
        elif not line.strip() or line.strip().startswith(("#", ";", "//")):
            continue
        else:
            if run >= minimum:
                count += 1
            run = 0
    return count + (run >= minimum)


def ext_of(url):
    path = url.split("?")[0].rstrip(".,")
    m = re.search(r"\.(tar\.gz|[A-Za-z0-9]{1,6})$", path)
    return m.group(1).lower() if m else ""


def image_kind(alt, url):
    key = f"{alt} {url}".lower()
    if re.search(r"wireshark|pcap|capture.*packet|tshark", key):
        return "packet_view"
    if re.search(r"screen ?shot|screen_shot|screenshot|capture|스크린|^image$|\bimage\b", key):
        return "screenshot_like"
    if re.search(r"grafana|graph|plot|chart|throughput|kpi|spectrum|constellation|scope|dashboard", key):
        return "chart"
    if re.search(r"diagram|topology|arch|flow|setup", key):
        return "diagram"
    return "unknown"


TEMPLATE_LINE = re.compile(r"_filename|\\[pcap\\]|provide the pcap|dump the (?:relevant )?packets?|tcpdump -i any -w free5gc|upload the `free5gc|add screenshots to help|if applicable, add|how to generate log files and pcaps|attach relevant logs", re.I)
HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
HEADING = re.compile(r"(?m)^\s*#{1,6}\s.*$")


def prose_of(text):
    text = FENCE.sub("", text)
    text = re.sub(r"https?://\S+|<img[^>]*>|\]\([^)]*\)", " ", text)
    return "\n".join(l for l in text.split("\n") if not CONFIG_LINE.match(l) and not TEMPLATE_LINE.search(l))


def analyze(text):
    feats = {}
    if not text:
        return feats, [], []
    text = HTML_COMMENT.sub("", text)
    prose = prose_of(HEADING.sub("", text))
    images = []
    for name, pattern in IMAGE_PATTERNS.items():
        for m in pattern.finditer(text):
            if name == "md_img":
                images.append((m.group(1), m.group(2), m.start()))
            else:
                images.append(("", m.group(1), m.start()))
    seen = {u for _, u, _ in images}
    for m in IMAGE_URL.finditer(text):
        if not any(m.group(0) in u or u in m.group(0) for u in seen):
            images.append(("", m.group(0), m.start()))
            seen.add(m.group(0))
    images = [(a, u, p) for a, u, p in images if not re.search(r"shields\.io|badge|avatar|gravatar|emoji", u, re.I)]
    attaches = []
    for m in ATTACH_URL.finditer(text):
        u = m.group(0)
        if any(u in iu or iu in u for _, iu, _ in images):
            continue
        if re.search(r"github\.com/[^/]+/[^/]+/(?:blob|tree|raw|commit|pull)/|review\.opendev|opendev\.org/.*/src|git\.openstack", u):
            continue
        attaches.append((u, m.start()))
    feats["image"] = len(images)
    feats["attach"] = len(attaches)
    feats["attach_exts"] = sorted({ext_of(u) or ("lp" if "launchpad" in u else "noext") for u, _ in attaches})
    feats["image_kinds"] = sorted({image_kind(a, u) for a, u, _ in images})
    feats["pcap_link"] = sum(1 for u, _ in attaches if re.search(r"pcap|\.cap\b", u, re.I))
    feats["pcap_mention"] = len(PCAP_MENTION.findall(prose))
    feats["attach_mention"] = len(ATTACH_MENTION.findall(prose))
    feats["external_log"] = len(EXTERNAL_LOG.findall(text))
    feats["screenshot_word"] = len(SCREENSHOT_WORD.findall(prose))
    feats["qxdm"] = len(QXDM.findall(text))
    bl = blocks(text)
    sizes = [len(lines) for _, lines, _ in bl]
    feats["fence_max"] = max(sizes, default=0)
    feats["fence_ge20"] = sum(s >= 20 for s in sizes)
    feats["fence_ge50"] = sum(s >= 50 for s in sizes)
    feats["fence_ge200"] = sum(s >= 200 for s in sizes)
    runs20, best = log_runs(text, 20)
    feats["logrun_ge20"] = runs20
    feats["logrun_max"] = best
    cfg = 0
    data = 0
    for lang, lines, _ in bl:
        if lang in CONFIG_LANG and len(lines) >= 5:
            cfg += 1
        elif lang in DATA_LANG and len(lines) >= 8:
            data += 1
        elif len(lines) >= 8 and sum(bool(CONFIG_LINE.match(l)) for l in lines) / len(lines) >= 0.6:
            cfg += 1
    if not bl:
        cfg += config_runs(text)
    feats["config_dump"] = cfg
    feats["data_dump"] = data
    feats["stack"] = sorted(k for k, p in STACK.items() if p.search(text))
    feats["crash_word"] = bool(CRASH_WORD.search(text))
    feats["chars"] = len(text)
    first_media = min([p for _, _, p in images] + [p for _, p in attaches], default=-1)
    feats["first_media_pos"] = first_media
    return feats, images, attaches


def source_records():
    for path in sorted((ROOT / "raw").glob("*.jsonl")):
        kind, *rest = path.stem.split("__")
        name = "/".join(rest)
        for line in path.open(encoding="utf-8"):
            raw = json.loads(line)
            if kind == "github":
                sid = f"{name}#{raw['number']}"
                body = raw.get("body") or ""
                comments = [c["body"] or "" for c in raw["comments"]["nodes"]]
            elif kind == "gitlab":
                sid = f"{name}#{raw['iid']}"
                body = raw.get("description") or ""
                comments = [n.get("body") or "" for n in raw.get("notes", [])]
            elif kind == "launchpad":
                sid = f"launchpad:{name}#{raw['id']}"
                body = raw.get("description") or ""
                comments = raw["messages"][1:]
            else:
                sid = f"rhbz#{raw['id']}"
                body = raw.get("cf_release_notes") or ""
                comments = []
            yield f"{kind}:{name}", sid, body, comments, raw


def main():
    canon = {}
    for line in (ROOT / "dataset" / "canonical.jsonl").open(encoding="utf-8"):
        row = json.loads(line)
        canon[row["source_id"]] = row
    out = (OUT / "features.jsonl").open("w", encoding="utf-8")
    media = (OUT / "media.jsonl").open("w", encoding="utf-8")
    for src, sid, body, comments, raw in source_records():
        fb, ib, ab = analyze(body)
        joined = "\n---\n".join(c for c in comments if c)
        fc, ic, ac = analyze(joined)
        row = canon.get(sid)
        rec = {
            "src": src, "sid": sid, "in_dataset": row is not None,
            "equipment": row and row["equipment"], "record_type": row and row["record_type"],
            "cause_basis": row and row["cause_basis"], "case_code": row and row["case_code"],
            "n_comments": len(comments), "body": fb, "comments": fc,
        }
        if src.startswith("gitlab"):
            rec["user_notes_count"] = raw.get("user_notes_count", 0)
        if src.startswith("github"):
            rec["comment_total"] = None
        out.write(json.dumps(rec, ensure_ascii=False) + "\n")
        if ib or ab or ic or ac:
            media.write(json.dumps({
                "sid": sid, "case_code": rec["case_code"],
                "body_images": [(a, u) for a, u, _ in ib], "body_attach": [u for u, _ in ab],
                "comment_images": [(a, u) for a, u, _ in ic], "comment_attach": [u for u, _ in ac],
                "body_len": len(body), "body_first_media": fb.get("first_media_pos", -1),
                "comments_len": len(joined), "comments_first_media": fc.get("first_media_pos", -1),
            }, ensure_ascii=False) + "\n")
    out.close()
    media.close()


if __name__ == "__main__":
    main()
