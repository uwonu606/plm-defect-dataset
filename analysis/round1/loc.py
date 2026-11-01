import json,sys,collections
recs=[json.loads(l) for l in open(sys.argv[1])]
parts=[collections.Counter() for _ in range(3)]
nparts=collections.Counter()
for r in recs:
    p=[x.strip() for x in (r.get('location') or '').split(' / ')]
    nparts[len(p)]+=1
    for i,x in enumerate(p[:3]): parts[i][x]+=1
print('n',len(recs),'parts dist',dict(nparts))
for i,c in enumerate(parts):
    print(i,'distinct',len(c),'singletons',sum(1 for v in c.values() if v==1),'top',c.most_common(15))
cc=collections.Counter(r.get('cause_class') or '' for r in recs); print(cc.most_common())
# variant spellings of a few NF names in module part
import re
for k in ['AMF','SMF','UPF','PFCP','NGAP','F1AP','GTP']:
    v=collections.Counter(x for x in parts[0]|parts[1] if re.search(k,x,re.I))
    print(k,len(v),list(v)[:12])
