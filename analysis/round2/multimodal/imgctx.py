import json, re, sys, random
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import scan
from agg import load
rows = {r["sid"]: r for r in load() if r["in_dataset"] and r["f"]["image"]}
K = [
 ("packet", re.compile(r"wireshark|pcap|packet|capture|tcpdump|NGAP|S1AP|PFCP|GTP|NAS|diameter|Request|Response|Accept|Reject|message", re.I)),
 ("log_terminal", re.compile(r"\blog|error|output|terminal|console|crash|stack|traceback|panic|command|shows?:|following", re.I)),
 ("ui_chart", re.compile(r"grafana|graph|plot|chart|throughput|dashboard|\bUI\b|NMS|page|button|browser|spectrum|constellation|iperf|speed", re.I)),
 ("diagram_setup", re.compile(r"diagram|topology|architecture|setup|deployment", re.I)),
]
per_img = Counter(); per_rec = Counter()
for src, sid, body, comments, raw in scan.source_records():
    if sid not in rows: continue
    text = scan.HTML_COMMENT.sub("", body + "\n---\n" + "\n---\n".join(c for c in comments if c))
    kinds = set()
    for pat in scan.IMAGE_PATTERNS.values():
        for m in pat.finditer(text):
            if scan.re.search(r"beacon|badge|shields", m.group(0)): continue
            ctx = text[max(0, m.start()-250):m.start()] + " " + (m.group(1) if m.lastindex else "")
            k = next((n for n, p in K if p.search(ctx)), "unknown")
            per_img[k] += 1; kinds.add(k)
    for k in kinds: per_rec[k] += 1
print("images by context", per_img, sum(per_img.values()))
print("records by context", per_rec, len(rows))
