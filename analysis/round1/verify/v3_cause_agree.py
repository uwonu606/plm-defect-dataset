import json,random,sys,collections
from math import comb
P="analysis/round1/profile"
sys.path.insert(0,P)
from extract import load, repo_of
C={r["case_code"]:r for r in load("canonical")}
ents=json.load(open(P+"/out/entities_canonical.json"))
pairs=json.load(open(P+"/out/pairs_all.json"))
# add file edges df<=10
g=collections.defaultdict(set)
for code,e in ents.items():
    for v in e["file"]: g[(repo_of(C[code]["source_id"]),v)].add(code)
for k,v in g.items():
    if 2<=len(v)<=10:
        v=sorted(v); pairs+= [("file",a,b) for i,a in enumerate(v) for b in v[i+1:]]
agree=collections.Counter(); tot=collections.Counter()
for kind,a,b in pairs:
    ra,rb=C[a],C[b]
    if ra["cause_basis"]=="명시" and rb["cause_basis"]=="명시":
        tot[kind]+=1; agree[kind]+= ra["cause_class"]==rb["cause_class"]
for k in tot: print(f"{k}: 명시-명시 pairs={tot[k]} same cause_class={agree[k]/tot[k]:.2f}")
# baselines
random.seed(0)
ex=[r for r in C.values() if r["cause_basis"]=="명시"]
by_repo=collections.defaultdict(list); by_re=collections.defaultdict(list)
for r in ex:
    by_repo[repo_of(r["source_id"])].append(r); by_re[(repo_of(r["source_id"]),r["equipment"])].append(r)
def base(groups):
    s=n=0
    for _ in range(20000):
        a=random.choice(ex); grp=groups(a)
        if len(grp)<2: continue
        b=random.choice(grp)
        if b is a: continue
        n+=1; s+= a["cause_class"]==b["cause_class"]
    return s/n
print("baseline random 명시 pair:", round(base(lambda a: ex),3))
print("baseline same repo:", round(base(lambda a: by_repo[repo_of(a["source_id"])]),3))
print("baseline same repo+equipment:", round(base(lambda a: by_re[(repo_of(a["source_id"]),a["equipment"])]),3))
# also record_type mixes
mix=collections.Counter()
for kind,a,b in pairs:
    if C[a]["record_type"]!=C[b]["record_type"]: mix[kind]+=1
print("pairs crossing record_type:", dict(mix), "of", dict(collections.Counter(k for k,_,_ in pairs)))
