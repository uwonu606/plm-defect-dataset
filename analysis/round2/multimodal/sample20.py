import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scan
from agg import load

ROOT = Path(".")
random.seed(20261101)
rows = [r for r in load() if r["in_dataset"] and r["record_type"] == "결함"]
img = [r for r in rows if r["f"]["image"] and not r["f"]["pcap_any"]]
pcap = [r for r in rows if r["f"]["pcap_file"] or (r["f"]["pcap_any"] and r["f"]["upload"])]
pick = random.sample(img, 10) + random.sample(pcap, 10)
ids = {r["sid"]: ("IMG" if i < 10 else "PCAP") for i, r in enumerate(pick)}
canon = {json.loads(l)["source_id"]: json.loads(l) for l in (ROOT / "dataset/canonical.jsonl").open(encoding="utf-8")}
CUE = re.compile(r"pcap|wireshark|screenshot|screen shot|image|picture|attached|attachment|your log|in the log|from the log|i see|i can see|looking at|captur|trace|\.zip|files/", re.I)
(Path(__file__).resolve().parent / "out" / "sample20_ids.json").write_text(json.dumps(ids, indent=1))
for src, sid, body, comments, raw in scan.source_records():
    if sid not in ids:
        continue
    c = canon[sid]
    print("=" * 100)
    print(ids[sid], sid, c["case_code"], c["cause_basis"], c["cause_class"])
    print("TITLE:", c["title"])
    print("CAUSE:", c["cause"][:400])
    print("RES:", c["resolution"][:250])
    b = scan.HTML_COMMENT.sub("", body)
    for m in scan.IMAGE_PATTERNS["md_img"].finditer(b):
        print("  BODY-IMG:", b[max(0, m.start() - 160):m.start()].replace("\n", " | ")[-160:], "->", m.group(1))
    for m in scan.IMAGE_PATTERNS["html_img"].finditer(b):
        print("  BODY-IMG:", b[max(0, m.start() - 160):m.start()].replace("\n", " | ")[-160:])
    for m in scan.PCAP_MENTION.finditer(scan.prose_of(b)):
        p = scan.prose_of(b)
        print("  BODY-PCAP:", p[max(0, m.start() - 120):m.end() + 80].replace("\n", " | "))
        break
    for i, cm in enumerate(comments):
        cm = scan.HTML_COMMENT.sub("", cm or "")
        hits = [m.start() for m in CUE.finditer(cm)]
        head = cm[:220].replace("\n", " | ")
        print(f"  C{i}: {head}")
        for h in hits[:2]:
            if h > 220:
                print(f"     ..{cm[max(0, h - 150):h + 150]}".replace("\n", " | "))
