import json,re,sys,collections
rows=[json.loads(l) for l in open(sys.argv[1])]
ver=re.compile(r'\bv?\d+\.\d+(\.\d+)?\b')
by=collections.Counter(); tot=collections.Counter()
for r in rows:
    src=r['source_id'].split('#')[0]
    tot[src]+=1
    parts=r['location'].split(' / ')
    if len(parts)>=3 and ver.search(parts[-1]): by[src]+=1
for s in tot: print(s,tot[s],by[s],round(by[s]/tot[s]*100))
pf=[r for r in rows if 'PFCP' in (r['title']+r['location']+r['problem']) and 'open5gs' in r['source_id']]
print('open5gs PFCP',len(pf), sum(1 for r in pf if re.search(r'2\.7\.[0-5]',r['location']+r['problem']+r['resolution'])))
print('dup pairs', sum(1 for r in rows if r['duplicate_of_case']))
