import json, sys, glob, os, re, statistics as s
judged = set("L-15 L-24 L-29 L-30 L-36 NEW-01 R-07 R-08 R-11 Y-01 Y-15 Y-21 L-48 L-61 R-15 Y-04 Y-13 L-12 R-05-b R-06 R-13 R-14-b Y-03 Y-05 Y-06 Y-07 Y-10 Y-11 Y-17 Y-25".split())
photo = set("L-12 L-15 L-61 NEW-01 R-11 R-14-b R-15 Y-03 Y-21".split())
photo_words = re.compile(r"사진|이미지|링크|첨부|캡처|재촬영|찍어")
rows = []
for p in glob.glob(os.path.join(sys.argv[1], "*.json")):
    d = json.load(open(p, encoding="utf-8"))
    cid = d.get("test_case_id")
    if cid not in judged: continue
    bot = [m["content"] for m in d["messages"] if m["role"] == "assistant"]
    acts = [a["action"] for a in d["action_log"]]
    photo_turns = sum(1 for b in bot if photo_words.search(b))
    rows.append((cid, len(bot), photo_turns, any(a.startswith("submit_") for a in acts), len(acts), os.path.basename(p)))
rows.sort()
for r in rows: print(*r, sep="\t")
print("n", len(rows))
for flag in (True, False):
    sub = [r for r in rows if (r[0] in photo) == flag]
    print(f"photo={flag} n={len(sub)} mean_bot_turns={s.mean(r[1] for r in sub):.2f} mean_turns_mentioning_photo={s.mean(r[2] for r in sub):.2f} any_submit={sum(r[3] for r in sub)}")
