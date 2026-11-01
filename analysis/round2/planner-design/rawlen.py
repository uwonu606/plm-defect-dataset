import json, sys
ch=[]; fm=[]
for line in open(sys.argv[1]):
    r=json.loads(line)
    if not r.get('in_dataset'): continue
    b=r['body']; c=r.get('comments') or {}
    total=b.get('chars',0)+(c.get('chars',0) if isinstance(c,dict) else 0)
    ch.append(total)
    f=max(b.get('fence_max',0), (c.get('fence_max',0) if isinstance(c,dict) else 0), b.get('logrun_max',0))
    if b.get('fence_ge20') or b.get('logrun_ge20') or (isinstance(c,dict) and c.get('fence_ge20')): fm.append(f)
def q(a):
    a=sorted(a); n=len(a); return dict(n=n,p50=a[n//2],p90=a[int(n*.9)],p99=a[int(n*.99)],max=a[-1])
print("raw chars per in-dataset record", q(ch))
print("max block lines among long-block records", q(fm))
