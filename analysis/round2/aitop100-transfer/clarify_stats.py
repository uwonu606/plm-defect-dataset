import json, sys, glob, re, os
state_dir = sys.argv[1]
photo = set("L-12 L-15 L-61 NEW-01 R-11 R-14-b R-15 Y-03 Y-21".split())
rows = []
for p in glob.glob(os.path.join(state_dir, "*.json")):
    d = json.load(open(p, encoding="utf-8"))
    cid = d.get("test_case_id")
    if not cid or cid.startswith(("tc_",)) :
        continue
    msgs = d["messages"]
    bot = [m["content"] for m in msgs if m["role"] == "assistant"]
    user = [m["content"] for m in msgs if m["role"] == "user"]
    asks = [i for i, b in enumerate(bot) if re.search(r"(\?|주세요|주시겠|알려 주|보내 주|첨부해)", b)]
    acts = [a["action"] for a in d["action_log"]]
    first_submit = next((i for i, a in enumerate(acts) if a.startswith("submit_")), None)
    nimg = sum(1 for u in user if "kakaocdn" in u or ".zip" in u or ".jpg" in u or ".png" in u)
    rows.append((cid, len(bot), len(asks), sum(len(b) for b in bot), any(a.startswith("submit_") for a in acts), nimg, cid in photo))
rows.sort()
print("case\tbot_turns\tturns_with_request\tchars\tsubmitted\timg_msgs\tphoto_case")
for r in rows: print(*r, sep="\t")
import statistics as s
for flag in (True, False):
    sub = [r for r in rows if r[6] == flag]
    if sub:
        print(f"photo={flag} n={len(sub)} mean_bot_turns={s.mean(r[1] for r in sub):.2f} mean_request_turns={s.mean(r[2] for r in sub):.2f} submitted={sum(r[4] for r in sub)}")
