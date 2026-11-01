import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agg import load

ROOT = Path(".")
rows = {r["sid"]: r for r in load() if r["in_dataset"]}
media = {json.loads(l)["sid"]: json.loads(l) for l in (Path(__file__).resolve().parent / "out/media.jsonl").open(encoding="utf-8")}

cands = {}
for line in (ROOT / "work/candidates.jsonl").open(encoding="utf-8"):
    c = json.loads(line)
    if c["source_id"] in rows:
        cands[c["source_id"]] = c
print("dataset rows", len(rows), "found in candidates", len(cands))

IMG_IN = re.compile(r"user-images\.githubusercontent|user-attachments/assets|/assets/\d+/|!\[|<img|/uploads/[0-9a-f]{32}/\S+\.(?:png|jpe?g|gif)|zenhubusercontent", re.I)
FILE_IN = re.compile(r"user-attachments/files|/files/\d+/|/uploads/[0-9a-f]{32}/|launchpadlibrarian", re.I)
img_rows = [s for s, r in rows.items() if r["f"]["image"]]
up_rows = [s for s, r in rows.items() if r["f"]["upload"]]
img_kept = sum(1 for s in img_rows if IMG_IN.search(cands[s]["body"] + cands[s]["discussion"]))
up_kept = sum(1 for s in up_rows if FILE_IN.search(cands[s]["body"] + cands[s]["discussion"]))
print(f"normalize 뒤(candidates) 이미지 링크가 남은 레코드: {img_kept}/{len(img_rows)}")
print(f"normalize 뒤 업로드 파일 링크가 남은 레코드: {up_kept}/{len(up_rows)}")

body_cut = sum(1 for r in rows.values() if r["body"].get("chars", 0) > 3000)
disc_cut = sum(1 for r in rows.values() if r["comments"].get("chars", 0) > 2500)
print(f"본문 3000자 초과로 잘린 레코드: {body_cut}/{len(rows)}, 댓글 합계 2500자 초과: {disc_cut}/{len(rows)}")
raw_chars = sum(r["body"].get("chars", 0) + r["comments"].get("chars", 0) for r in rows.values())
kept_chars = sum(len(c["body"]) + len(c["discussion"]) for c in cands.values())
print(f"본문+댓글 글자 수 raw {raw_chars:,} → candidates {kept_chars:,} ({100 * kept_chars / raw_chars:.1f}%)")
for key in ("longlog", "fence50", "stack", "config"):
    sel = [r for r in rows.values() if r["f"][key]]
    cut = sum(1 for r in sel if r["body"].get("chars", 0) > 3000 or r["comments"].get("chars", 0) > 2500)
    print(f"{key}: {len(sel)} 중 잘림 {cut} ({100 * cut / len(sel):.1f}%)")

canon = [json.loads(l) for l in (ROOT / "dataset/canonical.jsonl").open(encoding="utf-8")]
recs = [json.loads(l) for l in (ROOT / "dataset/records.jsonl").open(encoding="utf-8")]
TEXT = ("title", "location", "problem", "cause", "resolution")
WORDS = {
    "스크린샷·이미지·캡처": re.compile(r"스크린샷|screenshot|이미지|화면 캡처|캡처 화면|사진", re.I),
    "pcap·wireshark": re.compile(r"pcap|wireshark|tcpdump|패킷 캡처", re.I),
    "첨부": re.compile(r"첨부|attach(?:ed|ment)", re.I),
    "로그 파일": re.compile(r"로그 파일|log 파일|\.log\b", re.I),
    "URL": re.compile(r"https?://"),
}
by_sid = {c["source_id"]: c for c in canon}
for name, pat in WORDS.items():
    n = sum(1 for c in canon if pat.search(" ".join(c[k] for k in TEXT)))
    nr = sum(1 for c in recs if pat.search(" ".join(c[k] for k in TEXT)))
    print(f"canonical 서술에 '{name}': {n}, records: {nr}")
pat = WORDS["스크린샷·이미지·캡처"]
n = sum(1 for s in img_rows if pat.search(" ".join(by_sid[s][k] for k in TEXT)))
print(f"이미지 있는 레코드 중 canonical이 이미지를 언급: {n}/{len(img_rows)}")
pat = WORDS["pcap·wireshark"]
pc = [s for s, r in rows.items() if r["f"]["pcap_any"]]
n = sum(1 for s in pc if pat.search(" ".join(by_sid[s][k] for k in TEXT)))
print(f"pcap 언급 레코드 중 canonical이 pcap을 언급: {n}/{len(pc)}")
print("canonical 필드:", list(canon[0].keys()))
