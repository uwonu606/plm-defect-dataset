import json, sys, statistics as st
lens=[]
for line in open(sys.argv[1]):
    r=json.loads(line)
    s=" ".join(str(v) for v in r.values() if isinstance(v,str))
    lens.append(len(s))
lens.sort(); n=len(lens)
print("n",n,"mean",round(st.mean(lens)),"p50",lens[n//2],"p90",lens[int(n*.9)],"max",lens[-1])
print("top20 mean chars", 20*round(st.mean(lens)))
