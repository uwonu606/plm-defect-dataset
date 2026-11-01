import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scan
from agg import load

random.seed(int(sys.argv[2]) if len(sys.argv) > 2 else 7)
target = sys.argv[1]
rows = [r for r in load() if r["in_dataset"]]
texts = {}
want = {}
pool = [r for r in rows if r["f"][target] and (target != "pcap_any" or not r["f"]["pcap_file"])]
pick = {r["sid"] for r in random.sample(pool, min(10, len(pool)))}
for src, sid, body, comments, raw in scan.source_records():
    if sid in pick:
        texts[sid] = scan.HTML_COMMENT.sub("", body + "\n---\n" + "\n---\n".join(c for c in comments if c))
for sid, text in texts.items():
    print("=" * 10, sid)
    if target in ("pcap_any",):
        prose = scan.prose_of(scan.HEADING.sub("", text))
        for m in scan.PCAP_MENTION.finditer(prose):
            print("  ", prose[max(0, m.start() - 100):m.end() + 80].replace("\n", " | "))
            break
    elif target == "attach_mention":
        prose = scan.prose_of(scan.HEADING.sub("", text))
        for m in list(scan.ATTACH_MENTION.finditer(prose))[:2]:
            print("  ", prose[max(0, m.start() - 100):m.end() + 80].replace("\n", " | "))
    elif target == "stack":
        for k, p in scan.STACK.items():
            m = p.search(text)
            if m:
                print("  ", k, "::", text[max(0, m.start() - 60):m.end() + 120].replace("\n", " | "))
    elif target == "config":
        for lang, lines, _ in scan.blocks(text):
            if len(lines) >= 5:
                print("   lang=", lang, "lines=", len(lines), "::", " | ".join(lines[:6])[:300])
        if not scan.blocks(text):
            print("   (no fence) ", text[:200].replace("\n", " | "))
    elif target == "longlog":
        for lang, lines, _ in scan.blocks(text):
            if len(lines) >= 20:
                print("   fence lang=", lang, "lines=", len(lines), "::", " | ".join(lines[:3])[:250])
                break
        else:
            lines = text.split("\n")
            hits = [i for i, l in enumerate(lines) if scan.LOG_LINE.match(l)]
            print("   logrun ::", " | ".join(lines[hits[0]:hits[0] + 3])[:250] if hits else "?")
