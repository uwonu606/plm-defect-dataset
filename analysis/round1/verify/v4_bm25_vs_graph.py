import json,re,sys,math,collections
P="analysis/round1/profile"
sys.path.insert(0,P)
from extract import load, repo_of
C={r["case_code"]:r for r in load("canonical")}
R={r["case_code"]:r for r in load("records")}
def tok(s):
    s=s.lower(); out=re.findall(r"[a-z0-9_]{2,}",s)
    for run in re.findall(r"[가-힣]+",s):
        out += [run] if len(run)<2 else [run[i:i+2] for i in range(len(run)-1)]
    return out
F=["title","location","problem","cause","resolution"]
docs={c:tok(" ".join(R[c][f] or "" for f in F)) for c in R}
N=len(docs); avg=sum(map(len,docs.values()))/N
inv=collections.defaultdict(dict)
for c,t in docs.items():
    for w,n in collections.Counter(t).items(): inv[w][c]=n
idf={w:math.log(1+(N-len(p)+.5)/(len(p)+.5)) for w,p in inv.items()}
dl={c:len(t) for c,t in docs.items()}
def search(q, k1=1.2,b=0.75, filt=None):
    sc=collections.Counter()
    for w in set(q):
        if w not in inv: continue
        for c,n in inv[w].items():
            if filt and not filt(c): continue
            sc[c]+=idf[w]*n*(k1+1)/(n+k1*(1-b+b*dl[c]/avg))
    return [c for c,_ in sc.most_common(51)]
pairs=json.load(open(P+"/out/pairs_all.json"))
ents=json.load(open(P+"/out/entities_canonical.json"))
g=collections.defaultdict(set)
for code,e in ents.items():
    for v in e["file"]: g[(repo_of(C[code]["source_id"]),v)].add(code)
for k,v in g.items():
    if 2<=len(v)<=10:
        v=sorted(v); pairs+=[("file",a,b) for i,a in enumerate(v) for b in v[i+1:]]
ON={"dup","xref","func","err_specific","file"}
weak={"추론","미상"}
nb=collections.defaultdict(lambda: collections.defaultdict(set))
for kind,a,b in pairs:
    for s,t in ((a,b),(b,a)):
        if C[s]["cause_basis"] in weak and C[t]["cause_basis"]=="명시":
            nb[s][t].add(kind)
seeds_on={s for s,d in nb.items() if any(k&ON for k in d.values())}
print("weak seeds with 명시 1-hop neighbor: all edges", len(nb), "| ON edges only", len(seeds_on))
# query = seed title+problem only (symptom side)
stat=collections.Counter(); per_kind=collections.Counter(); per_kind_hit=collections.Counter()
for s in seeds_on:
    q=tok(R[s]["title"]+" "+R[s]["problem"])
    top=[c for c in search(q) if c!=s][:20]
    repo=repo_of(C[s]["source_id"])
    topf=[c for c in search(q, filt=lambda c: repo_of(C[c]["source_id"])==repo) if c!=s][:20]
    targets={t for t,k in nb[s].items() if k&ON}
    hit=bool(targets & set(top)); hitf=bool(targets & set(topf))
    stat["seeds"]+=1; stat["bm25_top20_has_neighbor"]+=hit; stat["bm25+repo_filter_top20"]+=hitf
    stat["bm25_top5"]+=bool(targets & set(top[:5]))
    for t in targets:
        for k in nb[s][t]&ON:
            per_kind[k]+=1; per_kind_hit[k]+= t in topf
print(dict(stat))
print({k:f"{per_kind_hit[k]}/{per_kind[k]}" for k in per_kind}, "(neighbor pairs found by bm25+repo filter top20)")
