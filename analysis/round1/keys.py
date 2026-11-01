import json,re,sys,collections
p=sys.argv[1]
rows=[json.loads(l) for l in open(p)]
n=len(rows)
pat={
 'ver_semver':re.compile(r'\bv?\d+\.\d+(\.\d+)?(-rc\d+)?\b'),
 'nf':re.compile(r'\b(AMF|SMF|UPF|NRF|AUSF|UDM|UDR|PCF|NSSF|MME|SGW|PGW|HSS|PCRF|SGW-C|SGW-U|gNB|eNB|CU-CP|CU-UP|DU)\b'),
 'iface':re.compile(r'\b(N1|N2|N3|N4|N6|N11|S1AP|S1-U|S11|S5|S6a|NGAP|F1AP|E1AP|E2|PFCP|GTP-?U|Diameter|SCTP|NAS|RRC|X2|Xn)\b',re.I),
 'cell':re.compile(r'\b(PCI|cell[ _-]?id|NCI|ECGI|NR-?CGI|TAC)\b',re.I),
 'alarm':re.compile(r'\balarm\b|알람',re.I),
 'cve':re.compile(r'CVE-\d{4}-\d+'),
 'commit':re.compile(r'\b[0-9a-f]{7,40}\b'),
 'ticket':re.compile(r'(#\d{3,}|bug ?\d{5,}|MR ?!\d+|PR ?#?\d+)',re.I),
}
loc3=0
c=collections.Counter()
for r in rows:
    loc=r.get('location','')
    parts=[x.strip() for x in loc.split(' / ')]
    if len(parts)>=3 and pat['ver_semver'].search(parts[-1]): loc3+=1
    txt=' '.join(str(r.get(k,'')) for k in ('title','location','problem','cause','resolution'))
    for k,v in pat.items():
        if v.search(txt): c[k]+=1
print('n',n)
print('location 마지막 칸에 버전 패턴',loc3, round(loc3/n*100,1),'%')
for k,v in c.most_common(): print(k,v,round(v/n*100,1),'%')
yrs=collections.Counter(r['created'][:4] for r in rows)
print('years',sorted(yrs.items()))
