import json,sys,collections
f=sys.argv[1]
paths=collections.Counter(); ex={}
def walk(o,p):
    if isinstance(o,dict):
        for k,v in o.items():
            q=p+"."+k; paths[q]+=1
            if q not in ex and not isinstance(v,(dict,list)): ex[q]=repr(v)[:90]
            walk(v,q)
    elif isinstance(o,list):
        for x in o[:50]: walk(x,p+"[]")
n=0
with open(f) as fh:
    for line in fh:
        n+=1; walk(json.loads(line),"")
print(f,n)
for p,c in sorted(paths.items()):
    if any(s in p for s in ("avatar","author.","closed_by.","assignee","time_stats","_links","task_")): continue
    print(f"  {c:7d} {p}  {ex.get(p,'')}")
