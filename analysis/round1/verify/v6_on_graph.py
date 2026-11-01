import json,sys,re,collections
P="analysis/round1/profile"
sys.path.insert(0,P)
from extract import load, repo_of, record_text
C={r["case_code"]:r for r in load("canonical")}
pairs=json.load(open(P+"/out/pairs_all.json"))
ents=json.load(open(P+"/out/entities_canonical.json"))
g=collections.defaultdict(set)
for code,e in ents.items():
    for v in e["file"]: g[(repo_of(C[code]["source_id"]),v)].add(code)
for k,v in g.items():
    if 2<=len(v)<=10:
        v=sorted(v); pairs+=[("file",a,b) for i,a in enumerate(v) for b in v[i+1:]]
def comp(kinds):
    par={}
    def f(x):
        par.setdefault(x,x)
        while par[x]!=x: par[x]=par[par[x]]; x=par[x]
        return x
    for k,a,b in pairs:
        if k in kinds: par[f(a)]=f(b)
    cs=collections.Counter(f(x) for x in list(par))
    conn=set(par)
    ex=sum(1 for x in conn if C[x]["cause_basis"]=="명시")
    return len(conn), sorted(cs.values(),reverse=True)[:3], ex
for name,ks in [("ON (dup,xref,func,err,file)",{"dup","xref","func","err_specific","file"}),("ON without file",{"dup","xref","func","err_specific"}),("high-cause (dup,xref)",{"dup","xref"})]:
    n,top,ex=comp(ks); print(name, n, f"{n/100:.1f}%", "largest", top, "명시 connected", ex, f"{ex/4713:.1%}")
al=[c for c,r in C.items() if re.search(r"alarm|알람|경보",record_text(r),re.I)]
print("alarm/알람/경보 mentions", len(al))
al2=[c for c,r in C.items() if re.search(r"\balarms?\b|알람",record_text(r),re.I)]
print("strict alarm word", len(al2))
