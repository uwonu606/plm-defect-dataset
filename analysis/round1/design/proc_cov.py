import json, re, sys, collections
path = sys.argv[1]
PROC = {
 'Registration': r'\bregistration\b|\battach\b|registration request|initial ue message',
 'Deregistration/Detach': r'\bderegistration\b|\bdetach\b',
 'PDU Session': r'pdu session|pdn connectivity|create session|session establishment',
 'Handover': r'\bhandover\b|\bhandvoer\b|핸드오버|\bxn\s?ho\b|\bs1\s?ho\b',
 'Service Request/Paging': r'service request|\bpaging\b',
 'Authentication/Security': r'\bauthentication\b|security mode|\bsmc\b',
 'NG/S1/F1/E1 Setup': r'\b(ng|s1|f1|e1|x2|xn)\s?setup\b',
 'RRC Setup/Reestablish': r'rrc ?(setup|connection|reestablish|re-establish|reconfiguration)',
 'RACH/Random Access': r'\brach\b|random access|\bmsg[1-4]\b',
 'NF Registration/Discovery': r'nfmanagement|nnrf|nf register|nf discovery|\bnrf\b.*(register|discover)',
 'Charging/Policy': r'\bgx\b|\bgy\b|\bn7\b|\bpcf\b.*polic|charging',
 'Cell setup/Scheduling': r'\bscheduler\b|\bscheduling\b|cell setup|\bsib\d?\b',
}
SYM = {
 'crash/segfault': r'segfault|segmentation fault|\bcrash|core dump|비정상 종료|죽',
 'assert': r'assert',
 'hang/deadlock': r'\bhang|deadlock|stuck|먹통|멈',
 'memory leak/oom': r'memory leak|\bleak\b|out of memory|\boom\b|누수',
 'timeout': r'timeout|timed out|타임아웃',
 'fail/reject': r'\breject|\bfail',
 'build/test fail': r'compile|build fail|ci fail|test fail|빌드',
 'http 5xx/api error': r'\b50[0-4]\b|internal server error',
}
c = collections.Counter(); cs = collections.Counter(); n = 0
byo = collections.Counter(); ntot = collections.Counter(); nsym_any=0
for line in open(path):
    r = json.loads(line); n += 1
    t = ' '.join(str(r.get(k) or '') for k in ('title','problem','location')).lower()
    hit = [k for k, p in PROC.items() if re.search(p, t)]
    for k in hit: c[k] += 1
    ntot[r['origin']] += 1
    if hit: byo[r['origin']] += 1
    sh = [k for k, p in SYM.items() if re.search(p, t)]
    for k in sh: cs[k] += 1
    if sh: nsym_any += 1
print('records', n)
print('procedure any:', sum(byo.values()), {o: f'{byo[o]}/{ntot[o]}={byo[o]/ntot[o]:.1%}' for o in ntot})
for k, v in c.most_common(): print(f'  {k}: {v}')
print('symptom any:', nsym_any, f'{nsym_any/n:.1%}')
for k, v in cs.most_common(): print(f'  {k}: {v}')
