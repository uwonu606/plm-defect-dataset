import json,re,collections
D="./dataset/"
C=[json.loads(l) for l in open(D+"canonical.jsonl")]
R={json.loads(l)["case_code"]:json.loads(l) for l in open(D+"records.jsonl")}
print(len(C),len(R))
cnt=collections.Counter((r["cause_basis"],r["cause_class"]) for r in C)
for cc in ["결함 아님","설정","규격 미준수","프로토콜 처리"]:
    print(cc, sum(v for (b,c),v in cnt.items() if c==cc), "명시", cnt[("명시",cc)])
print(collections.Counter(r["cause_class"] for r in C))
print(collections.Counter(r["cause_basis"] for r in C))
print("cause_class empty by basis",collections.Counter(r["cause_basis"] for r in C if not r["cause_class"]))
# dup
d=[r for r in C if r["duplicate_of_case"]]
print("dup",len(d), collections.Counter((r["cause_basis"], next(x for x in C if x["case_code"]==r["duplicate_of_case"])["cause_basis"]) for r in d))
same=sum(1 for r in d if r["cause_class"]==next(x for x in C if x["case_code"]==r["duplicate_of_case"])["cause_class"])
print("dup same cause_class",same)
