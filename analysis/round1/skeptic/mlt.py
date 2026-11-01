import json,re,math,collections,sys
D="./dataset/"
S=sys.argv[1]
C={}
for l in open(D+"canonical.jsonl"):
    r=json.loads(l);C[r["case_code"]]=r
R={}
for l in open(D+"records.jsonl"):
    r=json.loads(l);R[r["case_code"]]=r
tok=re.compile(r"[A-Za-z0-9_]+|[가-힣]+")
def toks(t):
    out=[]
    for w in tok.findall(t.lower()):
        if re.match(r"[가-힣]",w):
            out+= [w[i:i+2] for i in range(max(1,len(w)-1))]
        else: out.append(w)
    return out
F=["title","problem","cause","resolution","location"]
ids=list(R)
docs=[toks(" ".join(str(R[i].get(f) or "") for f in F)) for i in ids]
N=len(docs);avg=sum(map(len,docs))/N
inv=collections.defaultdict(list)
for di,d in enumerate(docs):
    for t,c in collections.Counter(d).items(): inv[t].append((di,c))
idf={t:math.log(1+(N-len(p)+.5)/(len(p)+.5)) for t,p in inv.items()}
dl=[len(d) for d in docs]
def search(q,k=50):
    sc=collections.defaultdict(float)
    for t in set(toks(q)):
        if t not in inv or len(inv[t])>N*0.2: continue
        for di,c in inv[t]:
            sc[di]+=idf[t]*c*2.2/(c+1.2*(.25+.75*dl[di]/avg))
    return [ids[i] for i,_ in sorted(sc.items(),key=lambda x:-x[1])[:k]]
def q_of(i,fields=("title","problem")): return " ".join(str(R[i].get(f) or "") for f in fields)
pairs=json.load(open(S+"/profile/out/pairs_all.json"))
by=collections.defaultdict(list)
for t,a,b in pairs: by[t].append((a,b))
cache={}
def top(i,fields):
    key=(i,fields)
    if key not in cache: cache[key]=search(q_of(i,fields),50)
    return cache[key]
for fields in [("title","problem"),("title",)]:
    print("query fields",fields)
    for t,ps in by.items():
        h20=h50=0
        for a,b in ps:
            tp=top(a,fields)
            h20+= b in tp[:20]; h50+= b in tp
        print(f"  {t:14s} n={len(ps):5d} B in top20 {h20/len(ps):.1%} top50 {h50/len(ps):.1%}")
# cause inheritance
adj=collections.defaultdict(set)
for t,a,b in pairs: adj[a].add(b);adj[b].add(a)
seeds=[i for i in C if C[i]["cause_basis"] in("추론","미상") and any(C[j]["cause_basis"]=="명시" for j in adj[i])]
h=0;tot=0
for s in seeds:
    nb=[j for j in adj[s] if C[j]["cause_basis"]=="명시"]
    tp=top(s,("title","problem"))[:20]
    if any(j in tp for j in nb): h+=1
print("inherit seeds",len(seeds),"seed with >=1 명시 neighbor already in BM25 top20(title+problem query):",h, f"{h/len(seeds):.1%}")
